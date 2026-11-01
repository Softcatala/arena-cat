"""Afegeix a les respostes els indicadors d'activació i de rànquing.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
"""

import sqlalchemy as sa
from alembic import op

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "responses", sa.Column("active", sa.Boolean(), server_default="true", nullable=False)
    )
    op.add_column(
        "responses",
        sa.Column("included_in_ranking", sa.Boolean(), server_default="true", nullable=False),
    )
    op.add_column(
        "responses",
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_column("responses", "updated_at")
    op.drop_column("responses", "included_in_ranking")
    op.drop_column("responses", "active")
