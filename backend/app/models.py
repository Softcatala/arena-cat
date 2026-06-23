"""Model de dades d'Arena Cat.

Taules:
    - categories: les categories de tasca.
    - prompts:    les tasques d'avaluació.
    - respostes:  la resposta d'un model a un prompt.
    - vots:       el vot d'un usuari anònim comparant dues respostes d'un prompt.
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


class Guanyador(enum.Enum):
    """Resultat d'un vot: guanya A, guanya B, empat o cap de les dues."""

    a = "a"
    b = "b"
    empat = "empat"
    cap = "cap"


def _valors_enum(enum_cls: type[enum.Enum]) -> list[str]:
    """Desa a Postgres els *valors* de l'enum (no els noms)."""
    return [membre.value for membre in enum_cls]


class Categoria(Base):
    """Categoria de tasca d'avaluació."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codi: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    nom: Mapped[str] = mapped_column(String(128), nullable=False)
    descripcio: Mapped[str | None] = mapped_column(Text, nullable=True)


class Prompt(Base):
    """Tasca d'avaluació que es mostra a l'usuari."""

    __tablename__ = "prompts"
    __table_args__ = (UniqueConstraint("versio", "codi", name="uq_prompts_versio_codi"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    versio: Mapped[str] = mapped_column(String(32), nullable=False)
    codi: Mapped[str] = mapped_column(String(64), nullable=False)
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    creat_a: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    categoria: Mapped["Categoria"] = relationship()
    respostes: Mapped[list["Resposta"]] = relationship(
        back_populates="prompt", cascade="all, delete-orphan"
    )


class Resposta(Base):
    """Resposta d'un model concret a un prompt. Única per parella (prompt, model)."""

    __tablename__ = "respostes"
    __table_args__ = (
        UniqueConstraint("prompt_id", "model", name="uq_respostes_prompt_model"),
        # Permet que vots referenciï (prompt_id, id) amb una FK composta.
        UniqueConstraint("prompt_id", "id", name="uq_respostes_prompt_id_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prompt_id: Mapped[int] = mapped_column(
        ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False
    )
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # Metadades de la inferència (seed, temperatura, top_p, max_new_tokens, quantization...).
    metadades: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    creat_a: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    prompt: Mapped["Prompt"] = relationship(back_populates="respostes")


class Vot(Base):
    """Vot anònim que compara dues respostes (A i B) d'un mateix prompt."""

    __tablename__ = "vots"
    __table_args__ = (
        # Garanteix que les dues respostes pertanyen al prompt_id del vot.
        ForeignKeyConstraint(
            ["prompt_id", "resposta_a_id"],
            ["respostes.prompt_id", "respostes.id"],
            name="fk_vots_resposta_a",
        ),
        ForeignKeyConstraint(
            ["prompt_id", "resposta_b_id"],
            ["respostes.prompt_id", "respostes.id"],
            name="fk_vots_resposta_b",
        ),
        CheckConstraint("resposta_a_id <> resposta_b_id", name="ck_vots_respostes_diferents"),
        Index("ix_vots_prompt_id", "prompt_id"),
        Index("ix_vots_creat_a", "creat_a"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    prompt_id: Mapped[int] = mapped_column(ForeignKey("prompts.id"), nullable=False)
    resposta_a_id: Mapped[int] = mapped_column(Integer, nullable=False)
    resposta_b_id: Mapped[int] = mapped_column(Integer, nullable=False)
    guanyador: Mapped[Guanyador] = mapped_column(
        Enum(Guanyador, name="guanyador", values_callable=_valors_enum),
        nullable=False,
    )
    sessio_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    temps_resposta_s: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    creat_a: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    prompt: Mapped["Prompt"] = relationship()
