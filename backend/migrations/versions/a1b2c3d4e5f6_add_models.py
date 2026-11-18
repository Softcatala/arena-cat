"""Afegeix la taula de models i hi enllaça les respostes.

Revision ID: a1b2c3d4e5f6
Revises: e1f2a3b4c5d6
"""

import sqlalchemy as sa
from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "models",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("maker", sa.String(length=128), nullable=True),
        sa.Column("url", sa.String(length=512), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    # Els models ja amb respostes es registren amb l'identificador com a nom;
    # la càrrega d'inferències n'hi completa el fabricant i l'enllaç.
    op.execute("INSERT INTO models (id, name) SELECT DISTINCT model, model FROM responses")
    op.create_foreign_key("fk_responses_model_models", "responses", "models", ["model"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_responses_model_models", "responses", type_="foreignkey")
    op.drop_table("models")
