"""sales agent foundation tables

Revision ID: 0002_sales_agent_foundation
Revises: 0001_init_mvp
Create Date: 2026-05-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002_sales_agent_foundation"
down_revision: Union[str, None] = "0001_init_mvp"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sales_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_type", sa.String(length=16), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("sent_messages", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("call_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("talk_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revenue", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("plan_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("unplanned_payments_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unplanned_payments_sum", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("overdue_payments_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("overdue_payments_sum", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("call_patterns_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("meta_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "period_type", "period_start", "period_end", name="uq_sales_snapshot_period"),
    )

    op.create_table(
        "sales_agent_memory",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("memory_type", sa.String(length=16), nullable=False),
        sa.Column("period_key", sa.String(length=32), nullable=False),
        sa.Column("summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "memory_type", "period_key", name="uq_sales_memory_period"),
    )


def downgrade() -> None:
    op.drop_table("sales_agent_memory")
    op.drop_table("sales_snapshots")
