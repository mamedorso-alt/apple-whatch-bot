from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import DailyMetric, DailyScore, User

settings = get_settings()


def _clean_generated_text(text: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        return cleaned

    # Remove accidental fenced wrappers from model responses.
    if cleaned.startswith("```") and cleaned.endswith("```"):
        cleaned = cleaned.strip("`").strip()

    lines = [line.rstrip() for line in cleaned.splitlines()]
    compact: list[str] = []
    prev_blank = False
    for raw in lines:
        line = raw.strip()
        if line in {"---", "—", "___"}:
            continue
        is_blank = not line
        if is_blank and prev_blank:
            continue
        compact.append(raw if not is_blank else "")
        prev_blank = is_blank
    return "\n".join(compact).strip()


def _fallback_coach_text(lang: str, today_score: int | None, avg_score: int | None, avg_sleep_min: int | None, avg_steps: int | None) -> str:
    if lang == "en":
        score_line = f"Today score: {today_score}/100." if today_score is not None else "Today score is not available yet."
        avg_line = (
            f"7-day average: score {avg_score}/100, sleep {avg_sleep_min} min, steps {avg_steps}."
            if avg_score is not None and avg_sleep_min is not None and avg_steps is not None
            else "Not enough 7-day data for trend analysis yet."
        )
        action = (
            "Actions: protect 2 deep-work blocks, keep sleep schedule stable, add one extra walk."
            if (avg_score or 0) >= 70
            else "Actions: prioritize recovery sleep, reduce cognitive load, schedule one focused 60-minute block."
        )
        return f"AI Coach\n{score_line}\n{avg_line}\n{action}"

    score_line = f"Скор за сегодня: {today_score}/100." if today_score is not None else "Скор за сегодня пока недоступен."
    avg_line = (
        f"Среднее за 7 дней: скор {avg_score}/100, сон {avg_sleep_min} мин, шаги {avg_steps}."
        if avg_score is not None and avg_sleep_min is not None and avg_steps is not None
        else "Пока недостаточно данных за 7 дней для анализа тренда."
    )
    action = (
        "Действия: защити 2 блока deep work, держи стабильный график сна, добавь одну дополнительную прогулку."
        if (avg_score or 0) >= 70
        else "Действия: приоритет на восстановительный сон, снизь когнитивную нагрузку, запланируй один 60-минутный фокус-блок."
    )
    return f"AI Коуч\n{score_line}\n{avg_line}\n{action}"


def _collect_context(db: Session, user: User) -> dict[str, Any]:
    today = datetime.now(timezone.utc).date()
    context_days = max(3, settings.ai_coach_context_days)
    start_date = today.fromordinal(today.toordinal() - context_days + 1)

    scores = (
        db.query(DailyScore)
        .filter(DailyScore.user_id == user.id, DailyScore.date >= start_date, DailyScore.date <= today)
        .order_by(DailyScore.date.asc())
        .all()
    )
    metrics = (
        db.query(DailyMetric)
        .filter(DailyMetric.user_id == user.id, DailyMetric.date >= start_date, DailyMetric.date <= today)
        .order_by(DailyMetric.date.asc())
        .all()
    )

    today_score = next((s.focus_score for s in reversed(scores) if s.date == today), None)
    if scores:
        avg_score = round(sum(s.focus_score for s in scores) / len(scores))
    else:
        avg_score = None
    if metrics:
        avg_sleep_min = round(sum(m.sleep_min for m in metrics) / len(metrics))
        avg_steps = round(sum(m.steps for m in metrics) / len(metrics))
    else:
        avg_sleep_min = None
        avg_steps = None

    compact_scores = [{"date": str(s.date), "focus_score": s.focus_score, "mode": s.mode} for s in scores]
    compact_metrics = [
        {
            "date": str(m.date),
            "steps": m.steps,
            "active_kcal": float(m.active_kcal),
            "sleep_min": m.sleep_min,
            "resting_hr": float(m.resting_hr) if m.resting_hr is not None else None,
            "hrv_sdnn": float(m.hrv_sdnn) if m.hrv_sdnn is not None else None,
            "workouts_count": m.workouts_count,
        }
        for m in metrics
    ]
    return {
        "today": str(today),
        "today_score": today_score,
        "avg_score": avg_score,
        "avg_sleep_min": avg_sleep_min,
        "avg_steps": avg_steps,
        "scores": compact_scores,
        "metrics": compact_metrics,
    }


async def _generate_with_anthropic(lang: str, context: dict[str, Any]) -> str:
    if not settings.anthropic_api_key:
        raise RuntimeError("Anthropic API key is not configured")

    system_prompt = (
        "You are a productivity coach. Use only provided aggregated health and score data. "
        "Do not provide medical diagnosis. Keep response clean, compact and practical.\n"
        "Always follow this format exactly:\n"
        "1) Title line with one emoji.\n"
        "2) One short overall assessment sentence.\n"
        "3) Block 'Что хорошо' / 'What went well' with 2-3 bullet points.\n"
        "4) Block 'Что улучшить' / 'What to improve' with 2-3 bullet points.\n"
        "5) Block '3 шага на завтра' / '3 steps for tomorrow' with numbered 1..3 actions.\n"
        "No markdown separators like --- and no long intro/outro text."
    )
    user_prompt = (
        f"Language: {'English' if lang == 'en' else 'Russian'}\n"
        f"Date: {context['today']}\n"
        f"Context JSON:\n{context}"
    )

    async with httpx.AsyncClient(timeout=settings.anthropic_timeout_sec) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": settings.anthropic_model,
                "max_tokens": 300,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            },
        )
        response.raise_for_status()
        body = response.json()
        content = body.get("content", [])
        for block in content:
            if block.get("type") == "text":
                text = (block.get("text") or "").strip()
                if text:
                    return _clean_generated_text(text)
    raise RuntimeError("Empty response from Anthropic")


async def _generate_chat_with_anthropic(lang: str, context: dict[str, Any], user_message: str) -> str:
    if not settings.anthropic_api_key:
        raise RuntimeError("Anthropic API key is not configured")

    system_prompt = (
        "You are a concise productivity coach. "
        "Use only provided health/score context and user message. "
        "Do not provide medical diagnosis. Give practical, concrete advice.\n"
        "Formatting rules: short paragraphs, clean bullets when useful, no markdown separators (---), no noisy symbols."
    )
    user_prompt = (
        f"Language: {'English' if lang == 'en' else 'Russian'}\n"
        f"Date: {context['today']}\n"
        f"Context JSON:\n{context}\n\n"
        f"User message:\n{user_message}"
    )

    async with httpx.AsyncClient(timeout=settings.anthropic_timeout_sec) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": settings.anthropic_model,
                "max_tokens": 450,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            },
        )
        response.raise_for_status()
        body = response.json()
        content = body.get("content", [])
        for block in content:
            if block.get("type") == "text":
                text = (block.get("text") or "").strip()
                if text:
                    return _clean_generated_text(text)
    raise RuntimeError("Empty response from Anthropic")


async def compose_ai_coach_report(db: Session, user: User, day: date | None = None) -> str:
    # day kept for future extensibility, current MVP always uses latest rolling context.
    _ = day
    context = _collect_context(db, user)
    lang = user.language

    try:
        return await _generate_with_anthropic(lang=lang, context=context)
    except Exception:
        return _fallback_coach_text(
            lang=lang,
            today_score=context["today_score"],
            avg_score=context["avg_score"],
            avg_sleep_min=context["avg_sleep_min"],
            avg_steps=context["avg_steps"],
        )


async def compose_ai_chat_reply(db: Session, user: User, user_message: str, day: date | None = None) -> str:
    _ = day
    context = _collect_context(db, user)
    lang = user.language
    try:
        return await _generate_chat_with_anthropic(lang=lang, context=context, user_message=user_message)
    except Exception:
        base = _fallback_coach_text(
            lang=lang,
            today_score=context["today_score"],
            avg_score=context["avg_score"],
            avg_sleep_min=context["avg_sleep_min"],
            avg_steps=context["avg_steps"],
        )
        if lang == "en":
            return f"{base}\n\nI could not run full AI reasoning right now, but I can still help. Your question: {user_message}"
        return f"{base}\n\nСейчас не удалось запустить полный AI-разбор, но я могу помочь. Ваш вопрос: {user_message}"
