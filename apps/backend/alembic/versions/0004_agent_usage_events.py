"""agent usage events for spend tracking

Revision ID: 0004_agent_usage
Revises: 0003_assistant_v2
Create Date: 2026-05-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_agent_usage"
down_revision: Union[str, None] = "0003_assistant_v2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_usage_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("operation", sa.String(length=32), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(12, 6), nullable=False, server_default="0"),
    )
    op.create_index("ix_agent_usage_user_created", "agent_usage_events", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_agent_usage_user_created", table_name="agent_usage_events")
    op.drop_table("agent_usage_events")
