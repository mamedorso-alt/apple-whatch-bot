from __future__ import annotations

from app.db.models import SalesAgentMemory, SalesSnapshot, User
from app.schemas.sales import SalesSnapshotIn
from sqlalchemy.orm import Session


def upsert_sales_snapshot(db: Session, user: User, payload: SalesSnapshotIn) -> SalesSnapshot:
    row = (
        db.query(SalesSnapshot)
        .filter(
            SalesSnapshot.user_id == user.id,
            SalesSnapshot.period_type == payload.period_type,
            SalesSnapshot.period_start == payload.period_start,
            SalesSnapshot.period_end == payload.period_end,
        )
        .first()
    )
    if row is None:
        row = SalesSnapshot(
            user_id=user.id,
            period_type=payload.period_type,
            period_start=payload.period_start,
            period_end=payload.period_end,
        )
        db.add(row)

    row.sent_messages = payload.sent_messages
    row.call_attempts = payload.call_attempts
    row.talk_minutes = payload.talk_minutes
    row.revenue = payload.revenue
    row.plan_amount = payload.plan_amount
    row.unplanned_payments_count = payload.unplanned_payments_count
    row.unplanned_payments_sum = payload.unplanned_payments_sum
    row.overdue_payments_count = payload.overdue_payments_count
    row.overdue_payments_sum = payload.overdue_payments_sum
    row.call_patterns_json = [item.model_dump() for item in payload.call_patterns]
    row.meta_json = {"week_ending_weekday": payload.week_ending_weekday}

    period_key = (
        f"{payload.period_start.isoformat()}_{payload.period_end.isoformat()}"
        if payload.period_type == "week"
        else payload.period_start.strftime("%Y-%m")
    )
    memory = (
        db.query(SalesAgentMemory)
        .filter(
            SalesAgentMemory.user_id == user.id,
            SalesAgentMemory.memory_type == payload.period_type,
            SalesAgentMemory.period_key == period_key,
        )
        .first()
    )
    summary_json = {
        "period_type": payload.period_type,
        "period_start": payload.period_start.isoformat(),
        "period_end": payload.period_end.isoformat(),
        "revenue": float(payload.revenue),
        "plan_amount": float(payload.plan_amount) if payload.plan_amount is not None else None,
        "sent_messages": payload.sent_messages,
        "call_attempts": payload.call_attempts,
        "talk_minutes": payload.talk_minutes,
        "unplanned_payments_count": payload.unplanned_payments_count,
        "unplanned_payments_sum": float(payload.unplanned_payments_sum),
        "overdue_payments_count": payload.overdue_payments_count,
        "overdue_payments_sum": float(payload.overdue_payments_sum),
        "top_call_patterns": [item.model_dump() for item in payload.call_patterns[:3]],
    }
    if memory is None:
        memory = SalesAgentMemory(user_id=user.id, memory_type=payload.period_type, period_key=period_key, summary_json=summary_json)
        db.add(memory)
    else:
        memory.summary_json = summary_json

    db.commit()
    db.refresh(row)
    return row
