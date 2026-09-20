"""Afegeix la data d'acreditació dels usuaris.

Revision ID: f3c9d7a201b6
Revises: e7b2c8a91f04
"""

import sqlalchemy as sa
from alembic import op

revision = "f3c9d7a201b6"
down_revision = "e7b2c8a91f04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("qualified_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "qualified_at")
