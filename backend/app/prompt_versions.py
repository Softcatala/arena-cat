"""Selecció comuna de la revisió activa de cada prompt."""

from fastapi import HTTPException
from sqlalchemy import Numeric, cast, func, select
from sqlalchemy.orm import Session

from app.models import Prompt, Response

VERSION_PATTERN = r"^v([1-9][0-9]{0,30})$"


def active_prompt_ids():
    """Tria per codi la revisió més alta amb dues respostes de models diferents."""
    number = cast(func.substring(Prompt.version, VERSION_PATTERN), Numeric)
    ranked = (
        select(
            Prompt.id,
            func.row_number()
            .over(partition_by=Prompt.code, order_by=number.desc())
            .label("position"),
        )
        .join(Response, Response.prompt_id == Prompt.id)
        .where(number.is_not(None))
        .group_by(Prompt.id)
        # UNIQUE(prompt_id, model) garanteix que són models diferents.
        .having(func.count(Response.id) >= 2)
        .subquery()
    )
    return select(ranked.c.id).where(ranked.c.position == 1)


def require_active_prompt(db: Session, prompt_id: int) -> None:
    """Rebutja una tasca que ha quedat obsoleta des que es va emetre el token."""
    if (
        db.scalar(
            select(Prompt.id).where(Prompt.id == prompt_id, Prompt.id.in_(active_prompt_ids()))
        )
        is None
    ):
        raise HTTPException(status_code=410, detail="Aquesta versió del prompt ja no és activa.")
