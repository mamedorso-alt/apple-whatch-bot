import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UUID, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    timezone: Mapped[str] = mapped_column(Text, default="Asia/Baku", nullable=False)
    language: Mapped[str] = mapped_column(String(2), default="ru", nullable=False)
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    is_linked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    api_token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    link_codes: Mapped[list["LinkCode"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class LinkCode(Base):
    __tablename__ = "link_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="link_codes")


class DailyMetric(Base):
    __tablename__ = "daily_metrics"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_daily_metrics_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    steps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_kcal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    sleep_min: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sleep_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sleep_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resting_hr: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    hrv_sdnn: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    workouts_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class DailyScore(Base):
    __tablename__ = "daily_scores"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_daily_scores_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    focus_score: Mapped[int] = mapped_column(Integer, nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    reasons_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class MessageLog(Base):
    __tablename__ = "message_log"
    __table_args__ = (UniqueConstraint("user_id", "date", "message_type", name="uq_message_log_user_date_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    message_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
