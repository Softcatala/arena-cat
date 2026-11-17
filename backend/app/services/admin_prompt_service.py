"""Llistat i activació de prompts des de l'administració."""

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session as OrmSession

from app.models import Category, Prompt, Response
from app.schemas import (
    AdminPromptPatch,
    AdminPromptResponse,
    AdminPromptsResponse,
)


def _to_response(prompt: Prompt, category_code: str, response_count: int) -> AdminPromptResponse:
    return AdminPromptResponse(
        id=prompt.id,
        version=prompt.version,
        code=prompt.code,
        category_code=category_code,
        text=prompt.text,
        active=prompt.active,
        created_at=prompt.created_at,
        response_count=response_count,
    )


def list_prompts(
    db: OrmSession,
    *,
    limit: int,
    offset: int,
    version: str | None,
    category_code: str | None,
    active: bool | None,
) -> AdminPromptsResponse:
    """Retorna una pàgina de prompts per ordre d'identificador, amb el recompte de respostes."""
    filters = []
    if version is not None:
        filters.append(Prompt.version == version)
    if category_code is not None:
        filters.append(Category.code == category_code)
    if active is not None:
        filters.append(Prompt.active == active)

    responses = (
        select(Response.prompt_id, func.count(Response.id).label("n"))
        .group_by(Response.prompt_id)
        .subquery()
    )
    rows = db.execute(
        select(Prompt, Category.code, func.coalesce(responses.c.n, 0))
        .join(Category, Category.id == Prompt.category_id)
        .outerjoin(responses, responses.c.prompt_id == Prompt.id)
        .where(*filters)
        .order_by(Prompt.id)
        .limit(limit)
        .offset(offset)
    ).all()
    total = db.scalar(
        select(func.count(Prompt.id))
        .join(Category, Category.id == Prompt.category_id)
        .where(*filters)
    )
    return AdminPromptsResponse(
        total=total or 0,
        prompts=[_to_response(prompt, code, count) for prompt, code, count in rows],
    )


def update_prompt(db: OrmSession, prompt_id: int, payload: AdminPromptPatch) -> AdminPromptResponse:
    """Activa o desactiva un prompt; si és inactiu, no es serveix ni compta al rànquing."""
    prompt = db.get(Prompt, prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt no trobat")

    prompt.active = payload.active
    db.commit()
    db.refresh(prompt)

    category_code = db.scalar(select(Category.code).where(Category.id == prompt.category_id))
    response_count = db.scalar(
        select(func.count(Response.id)).where(Response.prompt_id == prompt_id)
    )
    return _to_response(prompt, category_code, response_count or 0)
