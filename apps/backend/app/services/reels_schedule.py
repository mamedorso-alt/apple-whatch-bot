from __future__ import annotations

import logging
from datetime import datetime, timedelta
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


async def run_reels_manual_with_user_topic(
    db: Session, telegram_user_id: int, chat_id: int, topic: str
) -> None:
    """Generate a script from the user's brief. Clears awaiting only after an atomic claim to avoid Telegram retries
    hitting the health coach while a long search+LLM call is still running."""
    settings = get_settings()
    claimed = (
        db.query(User)
        .filter(User.telegram_user_id == telegram_user_id, User.reels_awaiting_custom_topic.is_(True))
        .update({"reels_awaiting_custom_topic": False}, synchronize_session=False)
    )
    db.commit()
    if claimed == 0:
        logger.info("reels topic: skip (no awaiting claim) telegram_user_id=%s", telegram_user_id)
        return

    user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
    lang = user.language if user else "ru"
    tz_name = (user.timezone if user else None) or settings.default_timezone
    try:
        delivery_date = datetime.now(ZoneInfo(tz_name)).date()
    except Exception:
        delivery_date = datetime.now(ZoneInfo(settings.default_timezone)).date()

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


async def run_reels_manual_delivery(db: Session, telegram_user_id: int, chat_id: int) -> None:
    """Random internet-seeded script (e.g. /reel_auto or after canceling topic wait)."""
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
