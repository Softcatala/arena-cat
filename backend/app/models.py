"""Model de dades d'Arena Cat.

Taules:
    - categories: les categories de tasca.
    - prompts:    les tasques d'avaluació.
    - responses:  la resposta d'un model a un prompt.
    - votes:      el vot d'un usuari anònim comparant dues respostes d'un prompt.
"""

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Winner(enum.Enum):
    """Resultat d'un vot: guanya A, guanya B, empat o cap de les dues."""

    a = "a"
    b = "b"
    tie = "tie"
    neither = "neither"


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    """Desa a Postgres els *valors* de l'enum (no els noms)."""
    return [member.value for member in enum_cls]


class Category(Base):
    """Categoria de tasca d'avaluació."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class Prompt(Base):
    """Tasca d'avaluació que es mostra a l'usuari."""

    __tablename__ = "prompts"
    __table_args__ = (UniqueConstraint("version", "code", name="uq_prompts_version_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    category: Mapped["Category"] = relationship()
    responses: Mapped[list["Response"]] = relationship(
        back_populates="prompt", cascade="all, delete-orphan"
    )


class Response(Base):
    """Resposta d'un model concret a un prompt. Única per parella (prompt, model)."""

    __tablename__ = "responses"
    __table_args__ = (
        UniqueConstraint("prompt_id", "model", name="uq_responses_prompt_model"),
        # Permet que votes referenciï (prompt_id, id) amb una FK composta.
        UniqueConstraint("prompt_id", "id", name="uq_responses_prompt_id_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prompt_id: Mapped[int] = mapped_column(
        ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False
    )
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # Metadades de la inferència (seed, temperatura, top_p, max_new_tokens, quantization...).
    inference_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    prompt: Mapped["Prompt"] = relationship(back_populates="responses")


class Vote(Base):
    """Vot anònim que compara dues respostes (A i B) d'un mateix prompt."""

    __tablename__ = "votes"
    __table_args__ = (
        # Garanteix que les dues respostes pertanyen al prompt_id del vot.
        ForeignKeyConstraint(
            ["prompt_id", "response_a_id"],
            ["responses.prompt_id", "responses.id"],
            name="fk_votes_response_a",
        ),
        ForeignKeyConstraint(
            ["prompt_id", "response_b_id"],
            ["responses.prompt_id", "responses.id"],
            name="fk_votes_response_b",
        ),
        CheckConstraint("response_a_id <> response_b_id", name="ck_votes_responses_different"),
        Index("ix_votes_prompt_id", "prompt_id"),
        Index("ix_votes_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    prompt_id: Mapped[int] = mapped_column(ForeignKey("prompts.id"), nullable=False)
    response_a_id: Mapped[int] = mapped_column(Integer, nullable=False)
    response_b_id: Mapped[int] = mapped_column(Integer, nullable=False)
    winner: Mapped[Winner] = mapped_column(
        Enum(Winner, name="winner", values_callable=_enum_values),
        nullable=False,
    )
    session_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    response_time_s: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    prompt: Mapped["Prompt"] = relationship()
