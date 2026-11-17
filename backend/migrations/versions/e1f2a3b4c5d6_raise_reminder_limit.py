"""Eleva a trenta el límit de recordatoris seguits sense vots.

Revision ID: e1f2a3b4c5d6
Revises: d9f012345678
"""

from alembic import op

revision = "e1f2a3b4c5d6"
down_revision = "d9f012345678"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_users_reminder_count", "users", type_="check")
    op.create_check_constraint(
        "ck_users_reminder_count", "users", "reminder_count BETWEEN 0 AND 30"
    )


def downgrade() -> None:
    op.execute("UPDATE users SET reminder_count = 3 WHERE reminder_count > 3")
    op.drop_constraint("ck_users_reminder_count", "users", type_="check")
    op.create_check_constraint("ck_users_reminder_count", "users", "reminder_count BETWEEN 0 AND 3")
