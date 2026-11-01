"""Afegeix el rol d'administrador i el bloqueig d'usuaris.

Revision ID: a1b2c3d4e5f6
Revises: d9f012345678
"""

import sqlalchemy as sa
from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "d9f012345678"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("is_admin", sa.Boolean(), server_default="false", nullable=False)
    )
    op.add_column("users", sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint(
        "ck_users_admin_not_deleted", "users", "NOT is_admin OR deleted_at IS NULL"
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_admin_not_deleted", "users", type_="check")
    op.drop_column("users", "blocked_at")
    op.drop_column("users", "is_admin")
