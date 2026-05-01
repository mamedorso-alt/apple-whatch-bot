from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy.orm import Session

from uuid import UUID

from app.core.config import get_settings
from app.services.agent_usage import record_agent_usage
from app.db.models import SalesSnapshot, User

settings = get_settings()


def _to_float(value: Decimal | None) -> float:
    return float(value or 0)


def _pct(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return round((numerator / denominator) * 100, 1)


def _collect_sales_context(db: Session, user: User) -> dict[str, Any]:
    weekly_rows = (
        db.query(SalesSnapshot)
        .filter(SalesSnapshot.user_id == user.id, SalesSnapshot.period_type == "week")
        .order_by(SalesSnapshot.period_end.desc())
        .all()
    )
    monthly_rows = (
        db.query(SalesSnapshot)
        .filter(SalesSnapshot.user_id == user.id, SalesSnapshot.period_type == "month")
        .order_by(SalesSnapshot.period_end.desc())
        .all()
    )
    current_week = weekly_rows[0] if weekly_rows else None
    previous_week = weekly_rows[1] if len(weekly_rows) > 1 else None
    current_month = monthly_rows[0] if monthly_rows else None
    previous_month = monthly_rows[1] if len(monthly_rows) > 1 else None
    return {
        "today": date.today().isoformat(),
        "current_week": current_week,
        "previous_week": previous_week,
        "current_month": current_month,
        "previous_month": previous_month,
        "weekly_count": len(weekly_rows),
    }


def _build_fallback_summary(lang: str, context: dict[str, Any]) -> str:
    current_week = context["current_week"]
    previous_week = context["previous_week"]
    if current_week is None:
        return (
            "Недостаточно данных по продажам. Сначала загрузите недельный срез из сервиса аналитики."
            if lang != "en"
            else "Not enough sales data yet. Upload a weekly snapshot from analytics first."
        )

    revenue = _to_float(current_week.revenue)
    plan = _to_float(current_week.plan_amount)
    plan_pct = _pct(revenue, plan) if plan > 0 else None
    wow_revenue = None
    if previous_week:
        prev_revenue = _to_float(previous_week.revenue)
        wow_revenue = _pct(revenue - prev_revenue, prev_revenue) if prev_revenue > 0 else None

    top_patterns = current_week.call_patterns_json[:3]
    patterns_text = ", ".join(f"{item.get('pattern')} ({item.get('count')})" for item in top_patterns) if top_patterns else "-"

    if lang == "en":
        plan_line = f"Plan completion: {plan_pct}%." if plan_pct is not None else "Plan is not configured."
        wow_line = f"Revenue change vs previous week: {wow_revenue}%." if wow_revenue is not None else "No week-over-week comparison yet."
        return (
            f"Sales brief ({current_week.period_start} - {current_week.period_end})\n"
            f"Revenue: {revenue:.2f}\n"
            f"{plan_line}\n"
            f"{wow_line}\n"
            f"Unplanned payments: {current_week.unplanned_payments_count} ({_to_float(current_week.unplanned_payments_sum):.2f})\n"
            f"Overdue payments: {current_week.overdue_payments_count} ({_to_float(current_week.overdue_payments_sum):.2f})\n"
            f"Top call issues: {patterns_text}\n"
            "Actions: close overdue payments first, verify next-step discipline in calls, align activity with payment planning."
        )

    plan_line = f"Выполнение плана: {plan_pct}%." if plan_pct is not None else "План продаж не задан."
    wow_line = f"Изменение выручки к прошлой неделе: {wow_revenue}%." if wow_revenue is not None else "Сравнение с прошлой неделей пока недоступно."
    return (
        f"Сводка по продажам ({current_week.period_start} - {current_week.period_end})\n"
        f"Выручка: {revenue:.2f}\n"
        f"{plan_line}\n"
        f"{wow_line}\n"
        f"Незапланированные платежи: {current_week.unplanned_payments_count} ({_to_float(current_week.unplanned_payments_sum):.2f})\n"
        f"Просроченные платежи: {current_week.overdue_payments_count} ({_to_float(current_week.overdue_payments_sum):.2f})\n"
        f"Топ ошибок в звонках: {patterns_text}\n"
        "Действия: закройте просрочки в первую очередь, усилите фиксацию next step, синхронизируйте исходящую активность с планом оплат."
    )


async def _generate_sales_reply_with_anthropic(
    lang: str,
    context: dict[str, Any],
    user_message: str | None = None,
    *,
    user_id: UUID | None = None,
) -> str:
    if not settings.anthropic_api_key:
        raise RuntimeError("Anthropic API key is not configured")

    system_prompt = (
        "You are a sales analytics assistant for a business owner. "
        "Use only provided analytics context. No hallucinations. "
        "If data is missing, state it explicitly. "
        "Keep concise: facts, likely reason, and 1-3 actions."
    )
    prompt = (
        f"Language: {'English' if lang == 'en' else 'Russian'}\n"
        f"Context: {context}\n"
        f"Owner question: {user_message or 'Give weekly owner brief with risks and actions.'}"
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
                "max_tokens": 400,
                "system": system_prompt,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        response.raise_for_status()
        payload = response.json()
        usage = payload.get("usage") or {}
        in_t = int(usage.get("input_tokens") or 0)
        out_t = int(usage.get("output_tokens") or 0)
        for block in payload.get("content", []):
            if block.get("type") == "text" and (block.get("text") or "").strip():
                text = (block.get("text") or "").strip()
                if user_id is not None:
                    record_agent_usage(
                        user_id,
                        provider="anthropic",
                        model=settings.anthropic_model,
                        operation="sales_reply",
                        input_tokens=in_t,
                        output_tokens=out_t,
                    )
                return text
    raise RuntimeError("Empty response from Anthropic")


async def compose_sales_owner_reply(db: Session, user: User, user_message: str | None = None) -> str:
    context = _collect_sales_context(db, user)
    try:
        return await _generate_sales_reply_with_anthropic(
            user.language, context, user_message, user_id=user.id
        )
    except Exception:
        return _build_fallback_summary(user.language, context)
