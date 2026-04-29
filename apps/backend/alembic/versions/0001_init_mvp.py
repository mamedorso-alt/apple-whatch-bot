"""initial mvp schema

Revision ID: 0001_init_mvp
Revises:
Create Date: 2026-04-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_init_mvp"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("timezone", sa.Text(), nullable=False, server_default="Asia/Baku"),
        sa.Column("language", sa.String(length=2), nullable=False, server_default="ru"),
        sa.Column("telegram_user_id", sa.BigInteger(), unique=True, nullable=True),
        sa.Column("is_linked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("api_token_hash", sa.String(length=64), unique=True, nullable=False),
    )

    op.create_table(
        "link_codes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(length=16), unique=True, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "daily_metrics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("steps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_kcal", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("sleep_min", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sleep_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sleep_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resting_hr", sa.Numeric(10, 2), nullable=True),
        sa.Column("hrv_sdnn", sa.Numeric(10, 2), nullable=True),
        sa.Column("workouts_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "date", name="uq_daily_metrics_user_date"),
    )

    op.create_table(
        "daily_scores",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("focus_score", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("reasons_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.UniqueConstraint("user_id", "date", name="uq_daily_scores_user_date"),
    )

    op.create_table(
        "message_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("message_type", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "date", "message_type", name="uq_message_log_user_date_type"),
    )


def downgrade() -> None:
    op.drop_table("message_log")
    op.drop_table("daily_scores")
    op.drop_table("daily_metrics")
    op.drop_table("link_codes")
    op.drop_table("users")
