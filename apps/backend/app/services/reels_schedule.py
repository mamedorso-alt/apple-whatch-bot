from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import ReelsAgentDailyLog, User
from app.i18n.telegram import msg
from app.services.reels_agent import compose_reels_script_for_telegram_user
from app.services.reels_support import parse_reels_telegram_user_ids, reels_reply_keyboard_markup
from app.services.telegram import send_telegram_message, send_telegram_messages_chunked

logger = logging.getLogger(__name__)


def _is_within_window(now_local: datetime, target_hour: int, target_minute: int, window_minutes: int) -> bool:
    target = now_local.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    return target <= now_local < (target + timedelta(minutes=window_minutes))


async def run_reels_agent_scheduled(db: Session) -> dict[str, Any]:
    settings = get_settings()
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
    window_minutes = max(1, int(settings.reels_agent_send_window_minutes))
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
            body = await compose_reels_script_for_telegram_user(db, tid, user_topic=None)
            user = db.query(User).filter(User.telegram_user_id == tid).first()
            lang = user.language if user else "ru"

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


async def prompt_reels_topic_flow(db: Session, telegram_user_id: int, chat_id: int) -> None:
    """Ask the user for a topic / notes; next free-text message is consumed as the brief."""
    settings = get_settings()
    user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
    if not user:
        await send_telegram_message(chat_id, msg("ru", "link_usage"))
        return
    lang = user.language
    user.reels_awaiting_custom_topic = True
    db.commit()
    await send_telegram_message(
        chat_id,
        msg(lang, "reels_ask_topic"),
        reply_markup=reels_reply_keyboard_markup(lang),
    )


async def try_claim_reels_user_topic(
    db: Session, telegram_user_id: int, chat_id: int
) -> tuple[bool, str, date]:
    """Atomically clear reels_awaiting_custom_topic; send processing notice. Returns (claimed, lang, delivery_date)."""
    settings = get_settings()
    claimed = (
        db.query(User)
        .filter(User.telegram_user_id == telegram_user_id, User.reels_awaiting_custom_topic.is_(True))
        .update({"reels_awaiting_custom_topic": False}, synchronize_session=False)
    )
    db.commit()
    if claimed == 0:
        logger.info("reels topic: skip (no awaiting claim) telegram_user_id=%s", telegram_user_id)
        return False, "ru", datetime.now(ZoneInfo(settings.default_timezone)).date()

    user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
    lang = user.language if user else "ru"
    try:
        await send_telegram_message(chat_id, msg(lang, "reels_topic_processing"))
    except Exception:
        logger.exception("reels topic: failed to send processing notice")
    tz_name = (user.timezone if user else None) or settings.default_timezone
    try:
        delivery_date = datetime.now(ZoneInfo(tz_name)).date()
    except Exception:
        delivery_date = datetime.now(ZoneInfo(settings.default_timezone)).date()
    return True, lang, delivery_date


async def finish_reels_manual_user_topic_job(
    db: Session,
    telegram_user_id: int,
    chat_id: int,
    topic: str,
    lang: str,
    delivery_date: date,
) -> None:
    """Compose + send + log after claim; restore awaiting on failure."""
    try:
        body = await compose_reels_script_for_telegram_user(db, telegram_user_id, user_topic=topic)
        await send_telegram_messages_chunked(
            chat_id,
            body,
            reply_markup=reels_reply_keyboard_markup(lang),
        )
        db.add(
            ReelsAgentDailyLog(
                telegram_user_id=telegram_user_id,
                delivery_date=delivery_date,
                source="manual_topic",
                payload_preview=body[:500],
            )
        )
        db.commit()
    except Exception:
        logger.exception("reels manual topic failed telegram_user_id=%s", telegram_user_id)
        db.rollback()
        try:
            db.query(User).filter(User.telegram_user_id == telegram_user_id).update(
                {"reels_awaiting_custom_topic": True},
                synchronize_session=False,
            )
            db.commit()
        except Exception:
            logger.exception("reels manual topic: could not restore awaiting flag")
        raise


async def finish_reels_manual_user_topic_job_new_session(
    telegram_user_id: int,
    chat_id: int,
    topic: str,
    lang: str,
    delivery_date: date,
) -> None:
    """Same as finish_reels_manual_user_topic_job with a fresh DB session (Telegram webhook background)."""
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        await finish_reels_manual_user_topic_job(db, telegram_user_id, chat_id, topic, lang, delivery_date)
    except Exception:
        logger.exception("reels manual topic background failed telegram_user_id=%s", telegram_user_id)
        try:
            await send_telegram_message(chat_id, msg(lang, "generic_processing_error"))
        except Exception:
            logger.exception("reels manual topic: failed to send error to user")
    finally:
        db.close()


async def run_reels_manual_with_user_topic(
    db: Session, telegram_user_id: int, chat_id: int, topic: str
) -> None:
    """Generate a script from the user's brief (tests / in-process callers use the passed Session)."""
    ok, lang, ddate = await try_claim_reels_user_topic(db, telegram_user_id, chat_id)
    if not ok:
        return
    await finish_reels_manual_user_topic_job(db, telegram_user_id, chat_id, topic, lang, ddate)


async def deliver_reels_manual_random_with_db(db: Session, telegram_user_id: int, chat_id: int) -> None:
    """Random internet-seeded script using caller's Session."""
    settings = get_settings()
    user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
    lang = user.language if user else "ru"
    tz_name = (user.timezone if user else None) or settings.default_timezone
    try:
        delivery_date = datetime.now(ZoneInfo(tz_name)).date()
    except Exception:
        delivery_date = datetime.now(ZoneInfo(settings.default_timezone)).date()

    body = await compose_reels_script_for_telegram_user(db, telegram_user_id, user_topic=None)
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


async def deliver_reels_manual_random_new_session(telegram_user_id: int, chat_id: int) -> None:
    """Random reel for /reel_auto — fresh Session for webhook background."""
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        await deliver_reels_manual_random_with_db(db, telegram_user_id, chat_id)
    except Exception:
        logger.exception("reels manual random delivery failed telegram_user_id=%s", telegram_user_id)
        db.rollback()
        try:
            u = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
            lang = u.language if u else "ru"
            await send_telegram_message(chat_id, msg(lang, "generic_processing_error"))
        except Exception:
            logger.exception("reels manual random: failed to send error")
    finally:
        db.close()


async def run_reels_manual_delivery(db: Session, telegram_user_id: int, chat_id: int) -> None:
    """Random internet-seeded script (e.g. /reel_auto); `db` is used for reads/writes."""
    await deliver_reels_manual_random_with_db(db, telegram_user_id, chat_id)
