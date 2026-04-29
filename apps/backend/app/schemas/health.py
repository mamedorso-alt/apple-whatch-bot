from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class DailyMetricsIn(BaseModel):
    date: date
    timezone: str = Field(default="Asia/Baku")
    steps: int = Field(default=0, ge=0)
    active_kcal: Decimal = Field(default=0, ge=0)
    sleep_min: int = Field(default=0, ge=0)
    sleep_start: datetime | None = None
    sleep_end: datetime | None = None
    resting_hr: Decimal | None = Field(default=None, ge=0)
    hrv_sdnn: Decimal | None = Field(default=None, ge=0)
    workouts_count: int = Field(default=0, ge=0)


class IngestResponse(BaseModel):
    status: str
