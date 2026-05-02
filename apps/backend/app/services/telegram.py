from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal

import httpx
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import LinkCode, MealLog, SalesSnapshot, User
from app.i18n.telegram import msg
from app.services.ai_coach import compose_ai_chat_reply, compose_ai_coach_report
from app.services.insights import build_daily_insight_text, build_weekly_trend_text
from app.services.nutrition_vision import analyze_food_image
from app.services.reports import compose_today_report, compose_week_report
from app.services.sales_assistant import compose_sales_owner_reply
from app.services.user_profile_service import get_or_create_profile, profile_to_read, record_weight, upsert_subjective
from app.services.voice import transcribe_telegram_media

settings = get_settings()

_CHUNK_LIMIT = 3800


def chunk_telegram_text(text: str, limit: int = _CHUNK_LIMIT) -> list[str]:
    raw = (text or "").strip()
    if not raw:
        return []
    if len(raw) <= limit:
        return [raw]
    parts: list[str] = []
    rest = raw
    while rest:
        if len(rest) <= limit:
            parts.append(rest)
            break
        cut = rest.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = limit
        parts.append(rest[:cut].strip())
        rest = rest[cut:].strip()
    return [p for p in parts if p]


async def send_telegram_messages_chunked(
    chat_id: int,
    text: str,
    reply_markup: dict | None = None,
) -> None:
    chunks = chunk_telegram_text(text)
    if not chunks:
        chunks = ["…"]
    for i, chunk in enumerate(chunks):
        await send_telegram_message(chat_id, chunk, reply_markup if i == 0 else None)


async def send_telegram_message(chat_id: int, text: str, reply_markup: dict | None = None) -> None:
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Telegram bot token is not configured")

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload: dict = {"chat_id": chat_id, "text": text[:4000]}
    if reply_markup:
        payload["reply_markup"] = reply_markup

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        body = response.json()
        if not body.get("ok"):
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Telegram API error")


async def answer_callback_query(callback_query_id: str, text: str | None = None) -> None:
    if not settings.telegram_bot_token:
        return
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/answerCallbackQuery"
    payload: dict = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text[:200]
        payload["show_alert"] = False
    async with httpx.AsyncClient(timeout=15) as client:
        await client.post(url, json=payload)


async def telegram_download_file(file_id: str) -> tuple[bytes, str]:
    if not settings.telegram_bot_token:
        raise RuntimeError("no token")
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/getFile",
            params={"file_id": file_id},
        )
        r.raise_for_status()
        res = r.json().get("result") or {}
        path = res.get("file_path") or ""
        if not path:
            raise RuntimeError("no file path")
        u = f"https://api.telegram.org/file/bot{settings.telegram_bot_token}/{path}"
        fr = await client.get(u)
        fr.raise_for_status()
        mime = "image/jpeg"
        if path.lower().endswith(".png"):
            mime = "image/png"
        return fr.content, mime


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


def _to_utc_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def link_telegram(db: Session, telegram_user_id: int, raw_code: str) -> str:
    code = raw_code.strip().upper()
    link_code = db.query(LinkCode).filter(LinkCode.code == code, LinkCode.used_at.is_(None)).first()
    if not link_code:
        return msg("ru", "link_invalid")

    now = datetime.now(timezone.utc)
    if _to_utc_aware(link_code.expires_at) < now:
        return msg("ru", "link_expired")

    user = db.query(User).filter(User.id == link_code.user_id).first()
    if user is None:
        return msg("ru", "link_invalid")

    # Same Telegram was tied to an older app user (reinstall / new device). A fresh code from the app
    # proves intent — move the binding to the user that owns this code.
    for stale in db.query(User).all():
        if stale.telegram_user_id == telegram_user_id and stale.id != user.id:
            stale.telegram_user_id = None
            stale.is_linked = False

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


def _latest_sales_snapshot(db: Session, user: User, period_type: str) -> SalesSnapshot | None:
    return (
        db.query(SalesSnapshot)
        .filter(SalesSnapshot.user_id == user.id, SalesSnapshot.period_type == period_type)
        .order_by(SalesSnapshot.period_end.desc())
        .first()
    )


def _sales_summary_for_command(user: User, row: SalesSnapshot | None, command: str) -> str:
    if row is None:
        return (
            "Нет данных по продажам. Сначала загрузите snapshot из аналитического сервиса."
            if user.language == "ru"
            else "No sales data yet. Upload a snapshot from analytics first."
        )

    revenue = float(row.revenue or 0)
    plan = float(row.plan_amount or 0)
    plan_pct = round((revenue / plan) * 100, 1) if plan > 0 else None
    if command == "/plan":
        if user.language == "en":
            return (
                f"Plan status ({row.period_start} - {row.period_end})\n"
                f"Revenue: {revenue:.2f}\n"
                f"Plan: {plan:.2f}\n"
                f"Completion: {plan_pct}%"
                if plan_pct is not None
                else f"Plan status ({row.period_start} - {row.period_end})\nRevenue: {revenue:.2f}\nPlan is not configured."
            )
        return (
            f"Статус плана ({row.period_start} - {row.period_end})\n"
            f"Выручка: {revenue:.2f}\n"
            f"План: {plan:.2f}\n"
            f"Выполнение: {plan_pct}%"
            if plan_pct is not None
            else f"Статус плана ({row.period_start} - {row.period_end})\nВыручка: {revenue:.2f}\nПлан продаж не задан."
        )

    if command == "/risks":
        if user.language == "en":
            return (
                f"Payment risks ({row.period_start} - {row.period_end})\n"
                f"Unplanned: {row.unplanned_payments_count} ({float(row.unplanned_payments_sum or 0):.2f})\n"
                f"Overdue: {row.overdue_payments_count} ({float(row.overdue_payments_sum or 0):.2f})"
            )
        return (
            f"Риски по оплатам ({row.period_start} - {row.period_end})\n"
            f"Незапланированные: {row.unplanned_payments_count} ({float(row.unplanned_payments_sum or 0):.2f})\n"
            f"Просроченные: {row.overdue_payments_count} ({float(row.overdue_payments_sum or 0):.2f})"
        )

    if command == "/actions":
        if user.language == "en":
            return (
                "Priority actions:\n"
                f"1) Close overdue payments ({row.overdue_payments_count}).\n"
                f"2) Review unplanned payments ({row.unplanned_payments_count}) and assign owners.\n"
                "3) Enforce next-step discipline in calls for this week."
            )
        return (
            "Приоритетные действия:\n"
            f"1) Закройте просроченные оплаты ({row.overdue_payments_count}).\n"
            f"2) Разберите незапланированные оплаты ({row.unplanned_payments_count}) и назначьте ответственных.\n"
            "3) Усильте контроль фиксации next step в звонках на этой неделе."
        )

    if user.language == "en":
        return (
            f"Sales period ({row.period_start} - {row.period_end})\n"
            f"Revenue: {revenue:.2f}\n"
            f"Messages: {row.sent_messages}, Calls: {row.call_attempts}, Talk minutes: {row.talk_minutes}"
        )
    return (
        f"Период продаж ({row.period_start} - {row.period_end})\n"
        f"Выручка: {revenue:.2f}\n"
        f"Сообщения: {row.sent_messages}, Звонки: {row.call_attempts}, Минуты на линии: {row.talk_minutes}"
    )


def profile_summary_for_telegram(db: Session, telegram_user_id: int) -> str:
    user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
    if not user:
        return msg("ru", "link_usage")
    p = get_or_create_profile(db, user)
    d = profile_to_read(p)
    if user.language == "en":
        lines = [
            "Profile:",
            f"Goal: {d['goal_type'] or '—'}",
            f"Height: {d['height_cm'] or '—'} cm",
            f"Last weight: {d['last_weight_kg'] or '—'}",
            "Edit in the iOS app or set weight: /weight 72.4",
        ]
    else:
        lines = [
            "Профиль:",
            f"Цель: {d['goal_type'] or '—'}",
            f"Рост: {d['height_cm'] or '—'} см",
            f"Последний вес: {d['last_weight_kg'] or '—'}",
            "Правки в приложении или вес: /weight 72.4",
        ]
    return "\n".join(lines)


def parse_weight_command(arg: str) -> Decimal | None:
    m = re.search(r"(\d+[.,]?\d*)", arg.replace(",", "."))
    if not m:
        return None
    try:
        return Decimal(m.group(1))
    except Exception:
        return None


def parse_mood_command(arg: str) -> tuple[int | None, int | None]:
    parts = arg.split()
    if len(parts) < 2:
        return None, None
    try:
        s = int(parts[0])
        f = int(parts[1])
        if 0 <= s <= 5 and 0 <= f <= 5:
            return s, f
    except ValueError:
        pass
    return None, None


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
    linked = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
    uid = linked.id if linked else None
    try:
        transcript = await transcribe_telegram_media(
            file_id=file_id, fallback_filename="voice.ogg", user_id=uid
        )
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
    if command in {"/insights", "/day"}:
        user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
        if not user:
            return msg("ru", "link_usage")
        return build_daily_insight_text(db, user, datetime.now(timezone.utc).date(), user.language)
    if command == "/trends":
        user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
        if not user:
            return msg("ru", "link_usage")
        return build_weekly_trend_text(db, user, datetime.now(timezone.utc).date(), user.language)
    if command == "/profile":
        return profile_summary_for_telegram(db, telegram_user_id)
    if command == "/weight":
        user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
        if not user:
            return msg("ru", "link_usage")
        w = parse_weight_command(arg) if arg else None
        if w is None:
            return msg(user_lang, "weight_usage")
        record_weight(db, user, w, datetime.now(timezone.utc))
        return msg(user_lang, "weight_saved")
    if command == "/mood":
        user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
        if not user:
            return msg("ru", "link_usage")
        stress, fatigue = parse_mood_command(arg)
        if stress is None:
            return msg(user_lang, "mood_usage")
        upsert_subjective(db, user, datetime.now(timezone.utc).date(), stress, fatigue, None)
        return msg(user_lang, "mood_saved")
    if command == "/meal":
        return msg(user_lang, "meal_help")

    return msg(user_lang, "unknown")


async def build_command_reply_async(db: Session, telegram_user_id: int, text: str) -> str:
    chunks = text.split(maxsplit=1)
    command = chunks[0].lower() if chunks else ""
    arg = chunks[1].strip() if len(chunks) > 1 else ""
    if command == "/coach":
        if arg:
            return await coach_chat_for_telegram(db, telegram_user_id, arg)
        return await coach_report_for_telegram(db, telegram_user_id)
    if command in {"/weekly", "/month", "/plan", "/risks", "/actions"}:
        user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
        if not user:
            return msg("ru", "link_usage")
        period_type = "month" if command == "/month" else "week"
        row = _latest_sales_snapshot(db, user, period_type=period_type)
        if command in {"/weekly", "/month"} and row:
            return await compose_sales_owner_reply(db, user)
        return _sales_summary_for_command(user, row, command)
    if command == "/ask":
        if not arg:
            return msg(language_for_telegram(db, telegram_user_id), "ask_usage")
        user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
        if user and _latest_sales_snapshot(db, user, period_type="week"):
            return await compose_sales_owner_reply(db, user, user_message=arg)
        return await coach_chat_for_telegram(db, telegram_user_id, arg)
    if text.strip() and not text.strip().startswith("/"):
        user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
        if user and _latest_sales_snapshot(db, user, period_type="week"):
            return await compose_sales_owner_reply(db, user, user_message=text.strip())
        return await coach_chat_for_telegram(db, telegram_user_id, text.strip())
    return build_command_reply(db, telegram_user_id, text)


async def handle_meal_photo(db: Session, user: User, chat_id: int, file_id: str) -> None:
    profile = get_or_create_profile(db, user)
    if not profile.food_logging_enabled:
        await send_telegram_message(chat_id, msg(user.language, "meal_disabled"))
        return
    try:
        data, mime = await telegram_download_file(file_id)
    except Exception:
        await send_telegram_message(chat_id, msg(user.language, "meal_download_failed"))
        return

    if not settings.openai_api_key and not settings.anthropic_api_key:
        await send_telegram_message(chat_id, msg(user.language, "meal_ai_missing"))
        return

    try:
        analyzed = await analyze_food_image(
            data, mime, user.language, profile.diet_notes, user_id=user.id
        )
    except RuntimeError:
        await send_telegram_message(chat_id, msg(user.language, "meal_ai_missing"))
        return
    except Exception:
        await send_telegram_message(chat_id, msg(user.language, "meal_analyze_failed"))
        return

    total = analyzed.get("total_kcal")
    conf = analyzed.get("confidence")
    desc = analyzed.get("description") or ""
    meal_guess = analyzed.get("meal_type_guess") or "unknown"
    try:
        conf_dec = Decimal(str(conf)) if conf is not None else None
    except Exception:
        conf_dec = None

    row = MealLog(
        user_id=user.id,
        photo_file_id=file_id,
        description_text=str(desc)[:2000],
        estimated_kcal=int(total) if total is not None else None,
        confidence=conf_dec,
        meal_type=str(meal_guess)[:16],
        raw_model_json=analyzed if isinstance(analyzed, dict) else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    if user.language == "en":
        lines = [
            "Meal estimate (approximate, not medical):",
            f"~ {total if total is not None else '?'} kcal",
            f"Confidence: {conf if conf is not None else '?'}",
            f"Guess: {meal_guess}",
            desc[:500] if desc else "",
        ]
    else:
        lines = [
            "Оценка приёма пищи (приблизительно, не медсовет):",
            f"~ {total if total is not None else '?'} ккал",
            f"Уверенность: {conf if conf is not None else '?'}",
            f"Тип: {meal_guess}",
            desc[:500] if desc else "",
        ]
    text = "\n".join(lines).strip()
    kb = {
        "inline_keyboard": [
            [{"text": "✓ OK" if user.language == "en" else "✓ Верно", "callback_data": f"m:{row.id}:ok"}],
        ]
    }
    await send_telegram_message(chat_id, text, reply_markup=kb)


async def handle_meal_callback(db: Session, telegram_user_id: int, data: str, callback_id: str) -> None:
    parts = data.split(":")
    if len(parts) != 3 or parts[0] != "m" or parts[2] != "ok":
        await answer_callback_query(callback_id, "Bad payload")
        return
    try:
        mid = int(parts[1])
    except ValueError:
        await answer_callback_query(callback_id, "Bad id")
        return
    user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
    if not user:
        await answer_callback_query(callback_id, "No user")
        return
    row = db.query(MealLog).filter(MealLog.id == mid, MealLog.user_id == user.id).first()
    if not row:
        await answer_callback_query(callback_id, "Not found")
        return
    row.user_confirmed = True
    db.commit()
    await answer_callback_query(callback_id, "Saved" if user.language == "en" else "Сохранено")
