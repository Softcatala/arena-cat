"""Registre de suspensos i correus per a l'activitat diària.

Revision ID: a2c4e6f80913
Revises: 61f5caa7fd83
"""

import sqlalchemy as sa
from alembic import op

revision = "a2c4e6f80913"
down_revision = "61f5caa7fd83"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "qualification_failures",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_qualification_failures_created_at", "qualification_failures", ["created_at"]
    )
    op.create_table(
        "email_deliveries",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "kind IN ('verification', 'password_reset')", name="ck_email_deliveries_kind"
        ),
    )
    op.create_index("ix_email_deliveries_created_at", "email_deliveries", ["created_at"])


def downgrade() -> None:
    op.drop_table("email_deliveries")
    op.drop_table("qualification_failures")
