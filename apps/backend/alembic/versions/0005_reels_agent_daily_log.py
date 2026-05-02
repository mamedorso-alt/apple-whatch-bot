"""reels agent daily delivery log

Revision ID: 0005_reels_agent
Revises: 0004_agent_usage
Create Date: 2026-05-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_reels_agent"
down_revision: Union[str, None] = "0004_agent_usage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reels_agent_daily_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("delivery_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("payload_preview", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_reels_agent_daily_scheduled",
        "reels_agent_daily_log",
        ["telegram_user_id", "delivery_date", "source"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_reels_agent_daily_scheduled", table_name="reels_agent_daily_log")
    op.drop_table("reels_agent_daily_log")
