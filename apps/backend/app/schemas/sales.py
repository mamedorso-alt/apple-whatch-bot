from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class CallPatternIn(BaseModel):
    pattern: str = Field(min_length=1, max_length=255)
    count: int = Field(ge=1)


class SalesSnapshotIn(BaseModel):
    period_type: str = Field(pattern="^(week|month)$")
    period_start: date
    period_end: date
    sent_messages: int = Field(default=0, ge=0)
    call_attempts: int = Field(default=0, ge=0)
    talk_minutes: int = Field(default=0, ge=0)
    revenue: Decimal = Field(default=0, ge=0)
    plan_amount: Decimal | None = Field(default=None, ge=0)
    unplanned_payments_count: int = Field(default=0, ge=0)
    unplanned_payments_sum: Decimal = Field(default=0, ge=0)
    overdue_payments_count: int = Field(default=0, ge=0)
    overdue_payments_sum: Decimal = Field(default=0, ge=0)
    call_patterns: list[CallPatternIn] = Field(default_factory=list)
    week_ending_weekday: int | None = Field(default=None, ge=0, le=6)


class IngestResponse(BaseModel):
    status: str
