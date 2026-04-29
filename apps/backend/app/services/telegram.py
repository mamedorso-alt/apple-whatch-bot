from __future__ import annotations

from datetime import datetime, timezone

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import LinkCode, User
from app.i18n.telegram import msg
from app.services.reports import compose_today_report, compose_week_report

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

    if user.telegram_user_id and user.telegram_user_id != telegram_user_id:
        return msg(user.language, "already_linked_other")

    user.telegram_user_id = telegram_user_id
    user.is_linked = True
    link_code.used_at = now
    db.commit()
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
