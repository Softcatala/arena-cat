"""Preferències i límits dels recordatoris per correu."""

import sqlalchemy as sa
from alembic import op

revision = "b7d8e9f01234"
down_revision = "a2c4e6f80913"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("reminder_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "users", sa.Column("reminder_count", sa.Integer(), nullable=False, server_default="0")
    )
    for name in ("reminder_consent_at", "reminder_sent_at", "reminder_invited_at"):
        op.add_column("users", sa.Column(name, sa.DateTime(timezone=True)))
    op.add_column("users", sa.Column("reminder_token", sa.String(64)))
    op.create_unique_constraint("uq_users_reminder_token", "users", ["reminder_token"])
    op.create_check_constraint("ck_users_reminder_count", "users", "reminder_count BETWEEN 0 AND 3")
    op.create_check_constraint(
        "ck_users_reminder_consent",
        "users",
        "NOT reminder_enabled OR (reminder_consent_at IS NOT NULL AND reminder_token IS NOT NULL)",
    )


def downgrade():
    for name in (
        "ck_users_reminder_consent",
        "ck_users_reminder_count",
        "uq_users_reminder_token",
    ):
        op.drop_constraint(name, "users")
    for name in (
        "reminder_token",
        "reminder_invited_at",
        "reminder_sent_at",
        "reminder_consent_at",
        "reminder_count",
        "reminder_enabled",
    ):
        op.drop_column("users", name)
