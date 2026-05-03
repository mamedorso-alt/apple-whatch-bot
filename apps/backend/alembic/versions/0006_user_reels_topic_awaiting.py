"""user reels topic awaiting flag

Revision ID: 0006_reels_await
Revises: 0005_reels_agent
Create Date: 2026-05-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_reels_await"
down_revision: Union[str, None] = "0005_reels_agent"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("reels_awaiting_custom_topic", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.alter_column("users", "reels_awaiting_custom_topic", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "reels_awaiting_custom_topic")
