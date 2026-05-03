from __future__ import annotations

import uuid
from typing import Any, Optional
from datetime import date as dt_date
from datetime import datetime as dt_datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UUID, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[dt_datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    timezone: Mapped[str] = mapped_column(Text, default="Asia/Baku", nullable=False)
    language: Mapped[str] = mapped_column(String(2), default="ru", nullable=False)
    telegram_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, unique=True, nullable=True)
    is_linked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    api_token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    reels_awaiting_custom_topic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    link_codes: Mapped[list["LinkCode"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    profile: Mapped[Optional["UserProfile"]] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class LinkCode(Base):
    __tablename__ = "link_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    expires_at: Mapped[dt_datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[dt_datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="link_codes")


class DailyMetric(Base):
    __tablename__ = "daily_metrics"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_daily_metrics_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[dt_date] = mapped_column(Date, nullable=False)
    steps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_kcal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    sleep_min: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sleep_start: Mapped[Optional[dt_datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sleep_end: Mapped[Optional[dt_datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resting_hr: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    hrv_sdnn: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    workouts_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[dt_datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class DailyScore(Base):
    __tablename__ = "daily_scores"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_daily_scores_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[dt_date] = mapped_column(Date, nullable=False)
    focus_score: Mapped[int] = mapped_column(Integer, nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    reasons_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class MessageLog(Base):
    __tablename__ = "message_log"
    __table_args__ = (UniqueConstraint("user_id", "date", "message_type", name="uq_message_log_user_date_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[dt_date] = mapped_column(Date, nullable=False)
    message_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    sent_at: Mapped[Optional[dt_datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    height_cm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sex: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    birth_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    goal_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    goal_target_weight_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    goal_horizon_date: Mapped[Optional[dt_date]] = mapped_column(Date, nullable=True)
    diet_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    medical_flags_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    quiet_hours_start: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    quiet_hours_end: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    weekly_weigh_in_weekday: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_weight_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    last_weight_at: Mapped[Optional[dt_datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    max_alerts_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    food_logging_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[dt_datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped[User] = relationship(back_populates="profile")


class UserBodyMetric(Base):
    __tablename__ = "user_body_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    recorded_at: Mapped[dt_datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")


class UserSubjectiveDaily(Base):
    __tablename__ = "user_subjective_daily"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_subjective_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[dt_date] = mapped_column(Date, nullable=False)
    stress_0_5: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fatigue_0_5: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class MealLog(Base):
    __tablename__ = "meal_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    logged_at: Mapped[dt_datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    meal_type: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")
    photo_file_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    estimated_kcal: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 3), nullable=True)
    macros_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    user_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    user_adjusted_kcal: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    raw_model_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)


class AlertLog(Base):
    __tablename__ = "alert_log"
    __table_args__ = (UniqueConstraint("user_id", "alert_date", "rule_id", name="uq_alert_user_date_rule"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    alert_date: Mapped[dt_date] = mapped_column(Date, nullable=False)
    rule_id: Mapped[str] = mapped_column(String(64), nullable=False)
    channel: Mapped[str] = mapped_column(String(16), nullable=False, default="telegram")
    payload_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sent_at: Mapped[dt_datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SalesSnapshot(Base):
    __tablename__ = "sales_snapshots"
    __table_args__ = (UniqueConstraint("user_id", "period_type", "period_start", "period_end", name="uq_sales_snapshot_period"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    period_type: Mapped[str] = mapped_column(String(16), nullable=False)
    period_start: Mapped[dt_date] = mapped_column(Date, nullable=False)
    period_end: Mapped[dt_date] = mapped_column(Date, nullable=False)
    sent_messages: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    call_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    talk_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revenue: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    plan_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    unplanned_payments_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unplanned_payments_sum: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    overdue_payments_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    overdue_payments_sum: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    call_patterns_json: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    meta_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[dt_datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[dt_datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AgentUsageEvent(Base):
    __tablename__ = "agent_usage_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[dt_datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    operation: Mapped[str] = mapped_column(String(32), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False, default=0)


class ReelsAgentDailyLog(Base):
    """One row per reels delivery (scheduled or manual) for auditing and scheduled dedup."""

    __tablename__ = "reels_agent_daily_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    delivery_date: Mapped[dt_date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[dt_datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    payload_preview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class SalesAgentMemory(Base):
    __tablename__ = "sales_agent_memory"
    __table_args__ = (UniqueConstraint("user_id", "memory_type", "period_key", name="uq_sales_memory_period"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    memory_type: Mapped[str] = mapped_column(String(16), nullable=False)
    period_key: Mapped[str] = mapped_column(String(32), nullable=False)
    summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[dt_datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[dt_datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
