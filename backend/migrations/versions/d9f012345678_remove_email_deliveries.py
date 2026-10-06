"""Elimina l'historial separat d'enviaments de correu."""

import sqlalchemy as sa
from alembic import op

revision = "d9f012345678"
down_revision = "c8e9f0123456"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("email_deliveries")


def downgrade():
    op.create_table(
        "email_deliveries",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "kind IN ('verification', 'password_reset', 'reminder')",
            name="ck_email_deliveries_kind",
        ),
    )
    op.create_index("ix_email_deliveries_created_at", "email_deliveries", ["created_at"])
