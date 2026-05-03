from __future__ import annotations

import logging
import threading

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.models import User
from app.db.session import get_db
from app.i18n.telegram import msg
from app.schemas.link import LinkCodeResponse
from app.services.linking import generate_link_code
from app.services.reels_schedule import (
    prompt_reels_topic_flow,
    run_reels_manual_delivery,
    run_reels_manual_with_user_topic,
)
from app.services.reels_support import REELS_TRIGGER_TEXTS, is_reels_allowlisted, reels_reply_keyboard_markup
from app.services.telegram import (
    build_command_reply_async,
    extract_incoming_text_or_reply,
    handle_meal_callback,
    handle_meal_photo,
    language_for_telegram,
    send_telegram_message,
)

router = APIRouter(prefix="/v1/telegram", tags=["telegram"])
logger = logging.getLogger(__name__)

_dedup_lock = threading.Lock()
_seen_telegram_update_ids: dict[int, None] = {}


def _is_duplicate_telegram_update(update_id: int | None) -> bool:
    """Telegram may retry the same update if our handler is slow; avoid double-processing (e.g. coach + reels)."""
    if update_id is None:
        return False
    with _dedup_lock:
        if update_id in _seen_telegram_update_ids:
            return True
        _seen_telegram_update_ids[update_id] = None
        if len(_seen_telegram_update_ids) > 8000:
            _seen_telegram_update_ids.clear()
        return False


@router.post("/link-code", response_model=LinkCodeResponse)
def create_link_code(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LinkCodeResponse:
    link_code = generate_link_code(db, current_user)
    return LinkCodeResponse(code=link_code.code, expires_at=link_code.expires_at)


@router.post("/webhook")
async def telegram_webhook(
    payload: dict,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    cfg = get_settings()
    if cfg.telegram_webhook_secret:
        if x_telegram_bot_api_secret_token != cfg.telegram_webhook_secret:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret")

    if _is_duplicate_telegram_update(payload.get("update_id")):
        return {"status": "ok"}

    cq = payload.get("callback_query")
    if cq:
        from_user = cq.get("from") or {}
        telegram_user_id = from_user.get("id")
        data = (cq.get("data") or "").strip()
        cq_id = cq.get("id")
        if telegram_user_id and data and cq_id:
            try:
                await handle_meal_callback(db, telegram_user_id, data, cq_id)
            except Exception:
                logger.exception("meal callback failed")
        return {"status": "ok"}

    message = payload.get("message") or {}
    chat = message.get("chat") or {}
    from_user = message.get("from") or {}
    chat_id = chat.get("id")
    telegram_user_id = from_user.get("id")

    if chat_id is None or telegram_user_id is None:
        return {"status": "ignored"}

    photos = message.get("photo") or []
    if photos:
        user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
        if not user or not user.is_linked:
            await send_telegram_message(chat_id=chat_id, text=msg(language_for_telegram(db, telegram_user_id), "link_usage"))
            return {"status": "ok"}
        file_id = photos[-1].get("file_id") or ""
        if not file_id:
            return {"status": "ignored"}
        try:
            await handle_meal_photo(db, user, chat_id, file_id)
        except Exception:
            logger.exception("meal photo failed")
            try:
                await send_telegram_message(
                    chat_id=chat_id,
                    text=msg(language_for_telegram(db, telegram_user_id), "generic_processing_error"),
                )
            except Exception:
                logger.exception("failed to send error to telegram")
        return {"status": "ok"}

    try:
        text, immediate_reply = await extract_incoming_text_or_reply(db, telegram_user_id, message)
        if immediate_reply:
            await send_telegram_message(chat_id=chat_id, text=immediate_reply)
            return {"status": "ok"}
        if not text:
            return {"status": "ignored"}

        user_lang = language_for_telegram(db, telegram_user_id)
        ts = text.strip()
        ts_low = ts.lower()
        user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()

        # /reel_auto — random topic immediately (also clears "waiting for topic" mode)
        if ts == "/reel_auto":
            if not cfg.reels_agent_enabled:
                await send_telegram_message(chat_id=chat_id, text=msg(user_lang, "reels_disabled"))
                return {"status": "ok"}
            if not is_reels_allowlisted(telegram_user_id):
                await send_telegram_message(chat_id=chat_id, text=msg(user_lang, "reels_not_allowed"))
                return {"status": "ok"}
            if user and user.reels_awaiting_custom_topic:
                user.reels_awaiting_custom_topic = False
                db.commit()
            try:
                await run_reels_manual_delivery(db, telegram_user_id, chat_id)
            except Exception:
                logger.exception("reels auto delivery failed")
                await send_telegram_message(
                    chat_id=chat_id,
                    text=msg(user_lang, "generic_processing_error"),
                )
            return {"status": "ok"}

        reels_ok = cfg.reels_agent_enabled and is_reels_allowlisted(telegram_user_id)
        if reels_ok and user and user.reels_awaiting_custom_topic:
            if ts_low in ("отмена", "cancel", "/cancel"):
                user.reels_awaiting_custom_topic = False
                db.commit()
                await send_telegram_message(
                    chat_id=chat_id,
                    text=msg(user_lang, "reels_topic_cancelled"),
                    reply_markup=reels_reply_keyboard_markup(user_lang),
                )
                return {"status": "ok"}
            if not ts.startswith("/"):
                if len(ts) < 12:
                    await send_telegram_message(
                        chat_id=chat_id,
                        text=msg(user_lang, "reels_topic_too_short"),
                        reply_markup=reels_reply_keyboard_markup(user_lang),
                    )
                    return {"status": "ok"}
                try:
                    await run_reels_manual_with_user_topic(db, telegram_user_id, chat_id, ts)
                except Exception:
                    logger.exception("reels manual topic delivery failed")
                    await send_telegram_message(
                        chat_id=chat_id,
                        text=msg(user_lang, "generic_processing_error"),
                    )
                return {"status": "ok"}
            user.reels_awaiting_custom_topic = False
            db.commit()

        is_reel_cmd = ts == "/reel" or ts in REELS_TRIGGER_TEXTS
        if is_reel_cmd:
            if not cfg.reels_agent_enabled:
                await send_telegram_message(chat_id=chat_id, text=msg(user_lang, "reels_disabled"))
                return {"status": "ok"}
            if not is_reels_allowlisted(telegram_user_id):
                await send_telegram_message(chat_id=chat_id, text=msg(user_lang, "reels_not_allowed"))
                return {"status": "ok"}
            try:
                await prompt_reels_topic_flow(db, telegram_user_id, chat_id)
            except Exception:
                logger.exception("reels topic prompt failed")
                await send_telegram_message(
                    chat_id=chat_id,
                    text=msg(user_lang, "generic_processing_error"),
                )
            return {"status": "ok"}

        reply = await build_command_reply_async(db, telegram_user_id, text)
        markup = None
        if cfg.reels_agent_enabled and is_reels_allowlisted(telegram_user_id):
            if ts_low == "/start" or ts_low.startswith("/start ") or ts_low == "/help" or ts_low.startswith("/help "):
                markup = reels_reply_keyboard_markup(user_lang)
        await send_telegram_message(chat_id=chat_id, text=reply, reply_markup=markup)
        return {"status": "ok"}
    except Exception:
        logger.exception("Telegram webhook processing failed")
        try:
            await send_telegram_message(
                chat_id=chat_id,
                text=msg(language_for_telegram(db, telegram_user_id), "generic_processing_error"),
            )
        except Exception:
            logger.exception("Failed to send Telegram processing error message")
        return {"status": "failed"}
