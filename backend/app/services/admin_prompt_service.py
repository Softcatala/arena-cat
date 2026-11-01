"""Alta, llistat i baixa de prompts des de l'administració."""

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession

from app.models import Category, Prompt, Response, text_sha256
from app.schemas import (
    AdminPromptCreate,
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
        content_sha256=prompt.content_sha256,
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


def create_prompt(db: OrmSession, payload: AdminPromptCreate) -> AdminPromptResponse:
    """Crea un prompt nou; rebutja el contingut repetit dins la versió i la parella versió-codi."""
    category = db.scalar(select(Category).where(Category.code == payload.category_code))
    if category is None:
        raise HTTPException(status_code=422, detail="Categoria desconeguda")

    duplicate = db.scalar(
        select(Prompt.id).where(
            Prompt.version == payload.version, Prompt.content_sha256 == text_sha256(payload.text)
        )
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Ja existeix un prompt amb el mateix contingut (id {duplicate})",
        )

    prompt = Prompt(
        version=payload.version, code=payload.code, category_id=category.id, text=payload.text
    )
    db.add(prompt)
    try:
        db.commit()
    except IntegrityError:
        # Una altra petició s'ha avançat entre la comprovació i l'alta.
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Ja existeix aquest prompt (versió i codi, o contingut a la versió)",
        ) from None
    db.refresh(prompt)
    return _to_response(prompt, category.code, 0)


def delete_prompt(db: OrmSession, prompt_id: int) -> None:
    """Esborra un prompt que no té cap inferència associada."""
    prompt = db.get(Prompt, prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt no trobat")

    has_responses = db.scalar(select(Response.id).where(Response.prompt_id == prompt_id).limit(1))
    if has_responses is not None:
        raise HTTPException(
            status_code=409, detail="El prompt té inferències associades i no es pot esborrar"
        )

    db.delete(prompt)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="El prompt encara està referenciat i no es pot esborrar"
        ) from None


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
