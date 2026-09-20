"""add users password_reset_sent_at

Revision ID: 61f5caa7fd83
Revises: 90421eb0233d
Create Date: 2026-09-20 13:17:48.407168

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "61f5caa7fd83"
down_revision: str | Sequence[str] | None = "90421eb0233d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("password_reset_sent_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "password_reset_sent_at")
