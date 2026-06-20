"""esquema inicial

Revision ID: f159ca3d2c6c
Revises:
Create Date: 2026-06-20 16:20:10.041226

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f159ca3d2c6c"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "prompts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("versio", sa.String(length=32), nullable=False),
        sa.Column("codi", sa.String(length=64), nullable=False),
        sa.Column(
            "categoria",
            sa.Enum("correccio", "reformulacio", "traduccio", name="categoria_tasca"),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "creat_a",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("versio", "codi", name="uq_prompts_versio_codi"),
    )
    op.create_table(
        "respostes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("prompt_id", sa.Integer(), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("metadades", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "creat_a",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["prompt_id"], ["prompts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("prompt_id", "model", name="uq_respostes_prompt_model"),
    )
    op.create_table(
        "vots",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("prompt_id", sa.Integer(), nullable=False),
        sa.Column("resposta_a_id", sa.Integer(), nullable=False),
        sa.Column("resposta_b_id", sa.Integer(), nullable=False),
        sa.Column(
            "guanyador",
            sa.Enum("a", "b", "empat", "cap", name="guanyador"),
            nullable=False,
        ),
        sa.Column("sessio_id", sa.String(length=128), nullable=True),
        sa.Column("temps_resposta_s", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column(
            "creat_a",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("resposta_a_id <> resposta_b_id", name="ck_vots_respostes_diferents"),
        sa.ForeignKeyConstraint(["prompt_id"], ["prompts.id"]),
        sa.ForeignKeyConstraint(["resposta_a_id"], ["respostes.id"]),
        sa.ForeignKeyConstraint(["resposta_b_id"], ["respostes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vots_creat_a", "vots", ["creat_a"], unique=False)
    op.create_index("ix_vots_prompt_id", "vots", ["prompt_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_vots_prompt_id", table_name="vots")
    op.drop_index("ix_vots_creat_a", table_name="vots")
    op.drop_table("vots")
    op.drop_table("respostes")
    op.drop_table("prompts")
    sa.Enum(name="guanyador").drop(op.get_bind())
    sa.Enum(name="categoria_tasca").drop(op.get_bind())
