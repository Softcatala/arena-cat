"""Registre dels correus de recordatori acceptats per SMTP."""

from alembic import op

revision = "c8e9f0123456"
down_revision = "b7d8e9f01234"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("ck_email_deliveries_kind", "email_deliveries", type_="check")
    op.create_check_constraint(
        "ck_email_deliveries_kind",
        "email_deliveries",
        "kind IN ('verification', 'password_reset', 'reminder')",
    )


def downgrade():
    op.execute("DELETE FROM email_deliveries WHERE kind = 'reminder'")
    op.drop_constraint("ck_email_deliveries_kind", "email_deliveries", type_="check")
    op.create_check_constraint(
        "ck_email_deliveries_kind",
        "email_deliveries",
        "kind IN ('verification', 'password_reset')",
    )
