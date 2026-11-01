"""Afegeix l'empremta SHA-256 del text dels prompts.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
"""

import sqlalchemy as sa
from alembic import op

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("prompts", sa.Column("content_sha256", sa.String(length=64), nullable=True))
    op.execute(
        "UPDATE prompts SET content_sha256 = encode(sha256(convert_to(text, 'UTF8')), 'hex')"
    )
    op.alter_column("prompts", "content_sha256", nullable=False)
    op.create_unique_constraint(
        "uq_prompts_version_content_sha256", "prompts", ["version", "content_sha256"]
    )
    op.create_check_constraint(
        "ck_prompts_content_sha256", "prompts", "content_sha256 ~ '^[0-9a-f]{64}$'"
    )


def downgrade() -> None:
    op.drop_constraint("ck_prompts_content_sha256", "prompts", type_="check")
    op.drop_constraint("uq_prompts_version_content_sha256", "prompts", type_="unique")
    op.drop_column("prompts", "content_sha256")
