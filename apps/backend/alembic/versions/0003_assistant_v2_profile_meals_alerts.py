"""assistant v2: profile, body metrics, subjective, meals, alert log

Revision ID: 0003_assistant_v2
Revises: 0002_sales_agent_foundation
Create Date: 2026-05-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_assistant_v2"
down_revision: Union[str, None] = "0002_sales_agent_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("height_cm", sa.Integer(), nullable=True),
        sa.Column("sex", sa.String(length=16), nullable=True),
        sa.Column("birth_year", sa.Integer(), nullable=True),
        sa.Column("goal_type", sa.String(length=32), nullable=True),
        sa.Column("goal_target_weight_kg", sa.Numeric(5, 2), nullable=True),
        sa.Column("goal_horizon_date", sa.Date(), nullable=True),
        sa.Column("diet_notes", sa.Text(), nullable=True),
        sa.Column("medical_flags_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("quiet_hours_start", sa.String(length=5), nullable=True),
        sa.Column("quiet_hours_end", sa.String(length=5), nullable=True),
        sa.Column("weekly_weigh_in_weekday", sa.Integer(), nullable=True),
        sa.Column("last_weight_kg", sa.Numeric(5, 2), nullable=True),
        sa.Column("last_weight_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_alerts_per_day", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("food_logging_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "user_body_metrics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("weight_kg", sa.Numeric(5, 2), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="manual"),
    )
    op.create_index("ix_user_body_metrics_user_recorded", "user_body_metrics", ["user_id", "recorded_at"])

    op.create_table(
        "user_subjective_daily",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("stress_0_5", sa.Integer(), nullable=True),
        sa.Column("fatigue_0_5", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.UniqueConstraint("user_id", "date", name="uq_subjective_user_date"),
    )

    op.create_table(
        "meal_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("meal_type", sa.String(length=16), nullable=False, server_default="unknown"),
        sa.Column("photo_file_id", sa.Text(), nullable=True),
        sa.Column("description_text", sa.Text(), nullable=True),
        sa.Column("estimated_kcal", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("macros_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("user_confirmed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("user_adjusted_kcal", sa.Integer(), nullable=True),
        sa.Column("raw_model_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index("ix_meal_log_user_logged", "meal_log", ["user_id", "logged_at"])

    op.create_table(
        "alert_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alert_date", sa.Date(), nullable=False),
        sa.Column("rule_id", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False, server_default="telegram"),
        sa.Column("payload_summary", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "alert_date", "rule_id", name="uq_alert_user_date_rule"),
    )


def downgrade() -> None:
    op.drop_table("alert_log")
    op.drop_table("meal_log")
    op.drop_table("user_subjective_daily")
    op.drop_table("user_body_metrics")
    op.drop_table("user_profiles")
