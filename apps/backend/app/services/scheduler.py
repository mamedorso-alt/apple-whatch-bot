from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import AlertLog, MessageLog, User
from app.services.insights import evaluate_alert_triggers, is_quiet_hours
from app.services.reports import compose_today_report, compose_week_report
from app.services.telegram import send_telegram_message
from app.services.user_profile_service import get_or_create_profile

settings = get_settings()


def _is_within_window(now_local: datetime, target_hour: int, target_minute: int, window_minutes: int) -> bool:
    target = now_local.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    return target <= now_local < (target + timedelta(minutes=window_minutes))


def _message_type_for_local_time(now_local: datetime) -> str | None:
    window_minutes = max(1, settings.scheduler_interval_min)
    if _is_within_window(now_local, settings.morning_send_hour, settings.morning_send_minute, window_minutes):
        return "morning"
    if _is_within_window(now_local, settings.evening_send_hour, settings.evening_send_minute, window_minutes):
        return "evening"
    return None


def _default_advice(lang: str, message_type: str) -> str:
    if lang == "en":
        return (
            "Tip: plan 2 deep-focus blocks for today."
            if message_type == "morning"
            else "Tip for tomorrow: keep sleep schedule stable."
        )
    return (
        "Совет: запланируйте 2 блока глубокого фокуса на сегодня."
        if message_type == "morning"
        else "Совет на завтра: держите стабильный режим сна."
    )


async def run_scheduled_reports(db: Session) -> dict[str, Any]:
    users = db.query(User).filter(User.is_linked.is_(True), User.telegram_user_id.is_not(None)).all()
    sent = 0
    skipped = 0

    for user in users:
        tz_name = user.timezone or settings.default_timezone
        try:
            now_local = datetime.now(ZoneInfo(tz_name))
        except Exception:
            now_local = datetime.now(ZoneInfo(settings.default_timezone))

        message_type = _message_type_for_local_time(now_local)
        if not message_type:
            skipped += 1
            continue

        send_date = now_local.date()
        log = MessageLog(user_id=user.id, date=send_date, message_type=message_type, status="pending")
        db.add(log)
        try:
            db.commit()
            db.refresh(log)
        except IntegrityError:
            db.rollback()
            skipped += 1
            continue

        if message_type == "morning":
            body = compose_today_report(db, user, datetime.now(timezone.utc).date())
        else:
            body = compose_week_report(db, user, datetime.now(timezone.utc).date())
        text = f"{body}\n\n{_default_advice(user.language, message_type)}"

        try:
            await send_telegram_message(chat_id=user.telegram_user_id, text=text)
            log.status = "sent"
            log.sent_at = datetime.now(timezone.utc)
            db.commit()
            sent += 1
        except Exception:
            db.rollback()
            failed = db.query(MessageLog).filter(MessageLog.id == log.id).first()
            if failed:
                failed.status = "failed"
                db.commit()
            skipped += 1

    smart = await run_smart_alerts(db)
    return {"sent": sent, "skipped": skipped, "smart_alerts": smart}


async def run_smart_alerts(db: Session) -> dict[str, int]:
    if not settings.smart_alerts_enabled:
        return {"sent": 0, "skipped": 0}
    users = db.query(User).filter(User.is_linked.is_(True), User.telegram_user_id.is_not(None)).all()
    sent = 0
    skipped = 0
    now_utc = datetime.now(timezone.utc)

    for user in users:
        tz_name = user.timezone or settings.default_timezone
        try:
            now_local = datetime.now(ZoneInfo(tz_name))
        except Exception:
            now_local = datetime.now(ZoneInfo(settings.default_timezone))

        profile = get_or_create_profile(db, user)
        if is_quiet_hours(now_local.hour, now_local.minute, profile.quiet_hours_start, profile.quiet_hours_end):
            skipped += 1
            continue

        send_date = now_local.date()
        already = db.query(AlertLog).filter(AlertLog.user_id == user.id, AlertLog.alert_date == send_date).count()
        if already >= max(1, profile.max_alerts_per_day):
            skipped += 1
            continue

        triggers = evaluate_alert_triggers(db, user, send_date, now_utc)
        for rule_id, text in triggers:
            if db.query(AlertLog).filter(AlertLog.user_id == user.id, AlertLog.alert_date == send_date).count() >= max(
                1, profile.max_alerts_per_day
            ):
                break
            log = AlertLog(user_id=user.id, alert_date=send_date, rule_id=rule_id, channel="telegram", payload_summary=text[:500])
            db.add(log)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                continue
            try:
                prefix = "🔔 "
                await send_telegram_message(chat_id=user.telegram_user_id, text=prefix + text)
                sent += 1
            except Exception:
                db.rollback()
                failed = (
                    db.query(AlertLog)
                    .filter(AlertLog.user_id == user.id, AlertLog.alert_date == send_date, AlertLog.rule_id == rule_id)
                    .first()
                )
                if failed:
                    db.delete(failed)
                    db.commit()
                skipped += 1

    return {"sent": sent, "skipped": skipped}
