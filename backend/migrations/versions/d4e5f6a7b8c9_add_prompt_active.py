"""Afegeix l'indicador d'activació als prompts.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
"""

import sqlalchemy as sa
from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "prompts", sa.Column("active", sa.Boolean(), server_default="true", nullable=False)
    )
    op.add_column(
        "prompts",
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_column("prompts", "updated_at")
    op.drop_column("prompts", "active")
