"""add task skips

Revision ID: d6a0f4c9b8e1
Revises: 5bcc14a623b7
Create Date: 2026-08-03 19:43:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d6a0f4c9b8e1"
down_revision: str | Sequence[str] | None = "5bcc14a623b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("task_skips"):
        return

    op.create_table(
        "task_skips",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("prompt_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("response_a_id", sa.Integer(), nullable=False),
        sa.Column("response_b_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "response_a_id <> response_b_id", name="ck_task_skips_responses_different"
        ),
        sa.ForeignKeyConstraint(["prompt_id"], ["prompts.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["prompt_id", "response_a_id"],
            ["responses.prompt_id", "responses.id"],
            name="fk_task_skips_response_a",
        ),
        sa.ForeignKeyConstraint(
            ["prompt_id", "response_b_id"],
            ["responses.prompt_id", "responses.id"],
            name="fk_task_skips_response_b",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_skips_user_id", "task_skips", ["user_id"], unique=False)
    op.create_index(
        "uq_task_skips_user_prompt_pair",
        "task_skips",
        [
            "user_id",
            "prompt_id",
            sa.literal_column("least(response_a_id, response_b_id)"),
            sa.literal_column("greatest(response_a_id, response_b_id)"),
        ],
        unique=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("task_skips"):
        return

    op.drop_index("uq_task_skips_user_prompt_pair", table_name="task_skips")
    op.drop_index("ix_task_skips_user_id", table_name="task_skips")
    op.drop_table("task_skips")
