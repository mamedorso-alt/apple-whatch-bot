from __future__ import annotations

from datetime import datetime, timezone

import httpx
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import LinkCode, User
from app.i18n.telegram import msg
from app.services.ai_coach import compose_ai_chat_reply, compose_ai_coach_report
from app.services.reports import compose_today_report, compose_week_report
from app.services.voice import transcribe_telegram_media

settings = get_settings()


async def send_telegram_message(chat_id: int, text: str) -> None:
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Telegram bot token is not configured")

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        body = response.json()
        if not body.get("ok"):
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Telegram API error")


def language_for_telegram(db: Session, telegram_user_id: int) -> str:
    user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
    return user.language if user else "ru"


def set_language(db: Session, telegram_user_id: int, lang: str) -> str:
    user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
    if not user:
        return msg("ru", "link_usage")
    user.language = "en" if lang == "en" else "ru"
    db.commit()
    return msg(user.language, "lang_updated_en" if user.language == "en" else "lang_updated_ru")


def link_telegram(db: Session, telegram_user_id: int, raw_code: str) -> str:
    code = raw_code.strip().upper()
    link_code = db.query(LinkCode).filter(LinkCode.code == code, LinkCode.used_at.is_(None)).first()
    if not link_code:
        return msg("ru", "link_invalid")

    now = datetime.now(timezone.utc)
    if link_code.expires_at < now:
        return msg("ru", "link_expired")

    user = db.query(User).filter(User.id == link_code.user_id).first()
    if user is None:
        return msg("ru", "link_invalid")

    # Prevent reassignment when this Telegram account is already bound elsewhere.
    already_bound = next(
        (u for u in db.query(User).all() if u.telegram_user_id == telegram_user_id and u.id != user.id),
        None,
    )
    if already_bound:
        return msg(user.language, "already_linked_other")

    if user.telegram_user_id and user.telegram_user_id != telegram_user_id:
        return msg(user.language, "already_linked_other")

    user.telegram_user_id = telegram_user_id
    user.is_linked = True
    link_code.used_at = now
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return msg(user.language, "already_linked_other")
    return msg(user.language, "link_success")


def today_report_for_telegram(db: Session, telegram_user_id: int) -> str:
    user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
    if not user:
        return msg("ru", "link_usage")
    return compose_today_report(db, user, datetime.now(timezone.utc).date())


def week_report_for_telegram(db: Session, telegram_user_id: int) -> str:
    user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
    if not user:
        return msg("ru", "link_usage")
    return compose_week_report(db, user, datetime.now(timezone.utc).date())


async def coach_report_for_telegram(db: Session, telegram_user_id: int) -> str:
    user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
    if not user:
        return msg("ru", "link_usage")
    return await compose_ai_coach_report(db, user, datetime.now(timezone.utc).date())


async def coach_chat_for_telegram(db: Session, telegram_user_id: int, user_message: str) -> str:
    user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
    if not user:
        return msg("ru", "link_usage")
    return await compose_ai_chat_reply(db, user, user_message, datetime.now(timezone.utc).date())


async def extract_incoming_text_or_reply(
    db: Session,
    telegram_user_id: int,
    message: dict,
) -> tuple[str | None, str | None]:
    text = (message.get("text") or "").strip()
    if text:
        return text, None

    voice = message.get("voice") or {}
    audio = message.get("audio") or {}
    file_id = (voice.get("file_id") or audio.get("file_id") or "").strip()
    if not file_id:
        return None, None

    lang = language_for_telegram(db, telegram_user_id)
    try:
        transcript = await transcribe_telegram_media(file_id=file_id, fallback_filename="voice.ogg")
    except RuntimeError as exc:
        code = str(exc)
        if code == "VOICE_NOT_CONFIGURED":
            return None, msg(lang, "voice_not_configured")
        return None, msg(lang, "voice_transcription_failed")
    except Exception:
        return None, msg(lang, "voice_transcription_failed")

    return transcript, None


def build_command_reply(db: Session, telegram_user_id: int, text: str) -> str:
    user_lang = language_for_telegram(db, telegram_user_id)
    chunks = text.split(maxsplit=1)
    command = chunks[0].lower() if chunks else ""
    arg = chunks[1].strip() if len(chunks) > 1 else ""

    if command == "/start":
        return msg(user_lang, "start")
    if command == "/help":
        return msg(user_lang, "help")
    if command == "/link":
        return msg(user_lang, "link_usage") if not arg else link_telegram(db, telegram_user_id, arg)
    if command == "/lang":
        if arg not in {"ru", "en"}:
            return msg(user_lang, "lang_usage")
        return set_language(db, telegram_user_id, arg)
    if command == "/today":
        return today_report_for_telegram(db, telegram_user_id)
    if command == "/week":
        return week_report_for_telegram(db, telegram_user_id)
    return msg(user_lang, "unknown")


async def build_command_reply_async(db: Session, telegram_user_id: int, text: str) -> str:
    chunks = text.split(maxsplit=1)
    command = chunks[0].lower() if chunks else ""
    arg = chunks[1].strip() if len(chunks) > 1 else ""
    if command == "/coach":
        if arg:
            return await coach_chat_for_telegram(db, telegram_user_id, arg)
        return await coach_report_for_telegram(db, telegram_user_id)
    if command == "/ask":
        if not arg:
            return msg(language_for_telegram(db, telegram_user_id), "ask_usage")
        return await coach_chat_for_telegram(db, telegram_user_id, arg)
    if text.strip() and not text.strip().startswith("/"):
        return await coach_chat_for_telegram(db, telegram_user_id, text.strip())
    return build_command_reply(db, telegram_user_id, text)
