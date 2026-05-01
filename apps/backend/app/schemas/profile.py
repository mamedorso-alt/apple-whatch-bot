from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_serializer


class MedicalFlags(BaseModel):
    chronic_condition: bool = False
    pregnancy: bool = False
    takes_medications: bool = False


class UserProfileRead(BaseModel):
    height_cm: int | None = None
    sex: str | None = None
    birth_year: int | None = None
    goal_type: str | None = None
    goal_target_weight_kg: Decimal | None = None
    goal_horizon_date: date | None = None
    diet_notes: str | None = None
    medical_flags: MedicalFlags = Field(default_factory=MedicalFlags)
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    weekly_weigh_in_weekday: int | None = Field(None, ge=0, le=6)
    last_weight_kg: Decimal | None = None
    last_weight_at: datetime | None = None
    max_alerts_per_day: int = 3
    food_logging_enabled: bool = True

    model_config = {"from_attributes": True}

    @field_serializer("goal_target_weight_kg", "last_weight_kg", when_used="json")
    def _weights_as_json_numbers(self, v: Decimal | None) -> float | None:
        """iOS expects JSON numbers; Pydantic otherwise encodes Decimal as strings."""
        if v is None:
            return None
        return float(v)


class UserProfileUpdate(BaseModel):
    height_cm: int | None = Field(None, ge=50, le=260)
    sex: str | None = Field(None, max_length=16)
    birth_year: int | None = Field(None, ge=1900, le=2100)
    goal_type: str | None = Field(None, max_length=32)
    goal_target_weight_kg: Decimal | None = None
    goal_horizon_date: date | None = None
    diet_notes: str | None = None
    medical_flags: MedicalFlags | None = None
    quiet_hours_start: str | None = Field(None, max_length=5, description="HH:MM")
    quiet_hours_end: str | None = Field(None, max_length=5, description="HH:MM")
    weekly_weigh_in_weekday: int | None = Field(None, ge=0, le=6)
    max_alerts_per_day: int | None = Field(None, ge=0, le=20)
    food_logging_enabled: bool | None = None


class WeightIngest(BaseModel):
    weight_kg: Decimal = Field(..., ge=20, le=400)
    recorded_at: datetime | None = None


class SubjectiveDailyIngest(BaseModel):
    date: date
    stress_0_5: int | None = Field(None, ge=0, le=5)
    fatigue_0_5: int | None = Field(None, ge=0, le=5)
    note: str | None = Field(None, max_length=2000)
