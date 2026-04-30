import logging

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.models import User
from app.db.session import get_db
from app.i18n.telegram import msg
from app.schemas.link import LinkCodeResponse
from app.services.linking import generate_link_code
from app.services.telegram import (
    build_command_reply_async,
    extract_incoming_text_or_reply,
    language_for_telegram,
    send_telegram_message,
)

router = APIRouter(prefix="/v1/telegram", tags=["telegram"])
settings = get_settings()
logger = logging.getLogger(__name__)


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
    if settings.telegram_webhook_secret:
        if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret")

    message = payload.get("message") or {}
    chat = message.get("chat") or {}
    from_user = message.get("from") or {}
    chat_id = chat.get("id")
    telegram_user_id = from_user.get("id")

    if chat_id is None or telegram_user_id is None:
        return {"status": "ignored"}

    try:
        text, immediate_reply = await extract_incoming_text_or_reply(db, telegram_user_id, message)
        if immediate_reply:
            await send_telegram_message(chat_id=chat_id, text=immediate_reply)
            return {"status": "ok"}
        if not text:
            return {"status": "ignored"}

        reply = await build_command_reply_async(db, telegram_user_id, text)
        await send_telegram_message(chat_id=chat_id, text=reply)
        return {"status": "ok"}
    except Exception:
        # Never return 5xx to Telegram, otherwise one bad update blocks the queue.
        logger.exception("Telegram webhook processing failed")
        try:
            await send_telegram_message(
                chat_id=chat_id,
                text=msg(language_for_telegram(db, telegram_user_id), "generic_processing_error"),
            )
        except Exception:
            logger.exception("Failed to send Telegram processing error message")
        return {"status": "failed"}
