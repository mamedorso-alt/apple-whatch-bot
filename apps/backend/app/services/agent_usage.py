from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import AgentUsageEvent, User
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


def estimate_cost_usd(provider: str, model: str, input_tokens: int, output_tokens: int) -> Decimal:
    """Rough list prices per 1M tokens (USD). For personal spend estimates only."""
    provider = (provider or "").lower()
    model_l = (model or "").lower()
    inp, out = Decimal(max(0, input_tokens)), Decimal(max(0, output_tokens))
    if provider == "anthropic":
        if "haiku" in model_l:
            rate_in, rate_out = Decimal("1.0"), Decimal("5.0")
        elif "opus" in model_l:
            rate_in, rate_out = Decimal("15.0"), Decimal("75.0")
        else:
            rate_in, rate_out = Decimal("3.0"), Decimal("15.0")
        return (inp * rate_in + out * rate_out) / Decimal(1_000_000)
    if provider == "openai":
        if "gpt-4o-mini" in model_l or "gpt-4o_mini" in model_l:
            rate_in, rate_out = Decimal("0.15"), Decimal("0.60")
        elif "gpt-4o" in model_l:
            rate_in, rate_out = Decimal("2.50"), Decimal("10.0")
        else:
            rate_in, rate_out = Decimal("0.15"), Decimal("0.60")
        return (inp * rate_in + out * rate_out) / Decimal(1_000_000)
    return Decimal("0")


def whisper_cost_usd_from_bytes(audio_byte_len: int) -> Decimal:
    """Whisper ~$0.006/min; crude duration estimate from compressed audio size."""
    if audio_byte_len <= 0:
        return Decimal("0.006") * Decimal("0.05")
    est_sec = max(3.0, min(600.0, float(audio_byte_len) / 2000.0))
    minutes = Decimal(str(est_sec / 60.0))
    return minutes * Decimal("0.006")


def record_agent_usage(
    user_id: UUID,
    *,
    provider: str,
    model: str,
    operation: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost_usd_override: Decimal | None = None,
) -> None:
    try:
        cost = (
            cost_usd_override
            if cost_usd_override is not None
            else estimate_cost_usd(provider, model, input_tokens, output_tokens)
        )
        db = SessionLocal()
        try:
            db.add(
                AgentUsageEvent(
                    user_id=user_id,
                    provider=provider[:32],
                    model=model[:128],
                    operation=operation[:32],
                    input_tokens=max(0, input_tokens),
                    output_tokens=max(0, output_tokens),
                    cost_usd=cost,
                )
            )
            db.commit()
        finally:
            db.close()
    except Exception:
        logger.exception("record_agent_usage failed user_id=%s op=%s", user_id, operation)


def _utc_window_for_local_calendar(user: User) -> tuple[datetime, datetime, datetime, datetime]:
    """Returns (day_start_utc, week_start_utc, month_start_utc, now_utc)."""
    tzname = (user.timezone or "UTC").strip() or "UTC"
    try:
        tz = ZoneInfo(tzname)
    except Exception:
        tz = ZoneInfo("UTC")
    now_local = datetime.now(tz)
    today: date = now_local.date()
    day_start_local = datetime.combine(today, time.min, tzinfo=tz)
    monday = today - timedelta(days=today.weekday())
    week_start_local = datetime.combine(monday, time.min, tzinfo=tz)
    month_start_local = datetime.combine(today.replace(day=1), time.min, tzinfo=tz)
    now_utc = now_local.astimezone(timezone.utc)
    return (
        day_start_local.astimezone(timezone.utc),
        week_start_local.astimezone(timezone.utc),
        month_start_local.astimezone(timezone.utc),
        now_utc,
    )


def sum_spend_usd(db: Session, user: User) -> dict[str, Decimal]:
    day_utc, week_utc, month_utc, end_utc = _utc_window_for_local_calendar(user)

    def _sum(since: datetime) -> Decimal:
        v = (
            db.query(func.coalesce(func.sum(AgentUsageEvent.cost_usd), 0))
            .filter(
                AgentUsageEvent.user_id == user.id,
                AgentUsageEvent.created_at >= since,
                AgentUsageEvent.created_at <= end_utc,
            )
            .scalar()
        )
        if v is None:
            return Decimal("0")
        return Decimal(str(v))

    return {
        "day_usd": _sum(day_utc),
        "week_usd": _sum(week_utc),
        "month_usd": _sum(month_utc),
    }
