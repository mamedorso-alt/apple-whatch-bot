from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import ReelsAgentDailyLog, User
from app.services.reels_agent import compose_reels_script_for_telegram_user
from app.services.reels_support import parse_reels_telegram_user_ids
from app.services.telegram import send_telegram_messages_chunked

logger = logging.getLogger(__name__)
settings = get_settings()


def _is_within_window(now_local: datetime, target_hour: int, target_minute: int, window_minutes: int) -> bool:
    target = now_local.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    return target <= now_local < (target + timedelta(minutes=window_minutes))


async def run_reels_agent_scheduled(db: Session) -> dict[str, Any]:
    if not settings.reels_agent_enabled:
        return {"sent": 0, "skipped": 0}

    ids = parse_reels_telegram_user_ids(settings.reels_agent_telegram_user_ids)
    if not ids:
        return {"sent": 0, "skipped": 0}

    tz_name = (settings.reels_agent_timezone or "").strip() or settings.default_timezone
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo(settings.default_timezone)

    now_local = datetime.now(tz)
    window_minutes = max(1, settings.scheduler_interval_min)
    if not _is_within_window(
        now_local,
        settings.reels_agent_daily_hour,
        settings.reels_agent_daily_minute,
        window_minutes,
    ):
        return {"sent": 0, "skipped": 0}

    send_date = now_local.date()
    sent = 0
    skipped = 0

    for tid in ids:
        already = (
            db.query(ReelsAgentDailyLog)
            .filter(
                ReelsAgentDailyLog.telegram_user_id == tid,
                ReelsAgentDailyLog.delivery_date == send_date,
                ReelsAgentDailyLog.source == "scheduled",
            )
            .first()
        )
        if already:
            skipped += 1
            continue

        try:
            body = await compose_reels_script_for_telegram_user(db, tid)
            user = db.query(User).filter(User.telegram_user_id == tid).first()
            lang = user.language if user else "ru"
            from app.services.reels_support import reels_reply_keyboard_markup

            await send_telegram_messages_chunked(
                tid,
                body,
                reply_markup=reels_reply_keyboard_markup(lang),
            )
            db.add(
                ReelsAgentDailyLog(
                    telegram_user_id=tid,
                    delivery_date=send_date,
                    source="scheduled",
                    payload_preview=body[:500],
                )
            )
            db.commit()
            sent += 1
        except Exception:
            logger.exception("reels scheduled delivery failed telegram_user_id=%s", tid)
            db.rollback()
            skipped += 1

    return {"sent": sent, "skipped": skipped}


async def run_reels_manual_delivery(db: Session, telegram_user_id: int, chat_id: int) -> None:
    user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
    lang = user.language if user else "ru"
    tz_name = (user.timezone if user else None) or settings.default_timezone
    try:
        delivery_date = datetime.now(ZoneInfo(tz_name)).date()
    except Exception:
        delivery_date = datetime.now(ZoneInfo(settings.default_timezone)).date()

    body = await compose_reels_script_for_telegram_user(db, telegram_user_id)
    from app.services.reels_support import reels_reply_keyboard_markup

    await send_telegram_messages_chunked(
        chat_id,
        body,
        reply_markup=reels_reply_keyboard_markup(lang),
    )
    db.add(
        ReelsAgentDailyLog(
            telegram_user_id=telegram_user_id,
            delivery_date=delivery_date,
            source="manual",
            payload_preview=body[:500],
        )
    )
    db.commit()
