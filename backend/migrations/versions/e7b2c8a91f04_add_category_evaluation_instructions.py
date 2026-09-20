"""add category evaluation instructions

Revision ID: e7b2c8a91f04
Revises: d6a0f4c9b8e1
"""

from collections.abc import Sequence

from alembic import op

revision: str = "e7b2c8a91f04"
down_revision: str | Sequence[str] | None = "d6a0f4c9b8e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Algunes instal·lacions ja tenen la columna des de la migració inicial.
    op.execute("ALTER TABLE categories ADD COLUMN IF NOT EXISTS evaluation_instructions TEXT")


def downgrade() -> None:
    op.drop_column("categories", "evaluation_instructions")
