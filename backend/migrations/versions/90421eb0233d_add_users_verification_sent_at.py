"""add users verification_sent_at

Revision ID: 90421eb0233d
Revises: f3c9d7a201b6
Create Date: 2026-09-20 11:42:30.012520

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "90421eb0233d"
down_revision: str | Sequence[str] | None = "f3c9d7a201b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("verification_sent_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "verification_sent_at")
