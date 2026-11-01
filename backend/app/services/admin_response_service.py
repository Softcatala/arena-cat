"""Alta, llistat, activació i baixa d'inferències (respostes de models) des de l'administració."""

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession

from app.models import Prompt, Response, TaskSkip, Vote
from app.schemas import (
    AdminResponseCreate,
    AdminResponseItem,
    AdminResponsePatch,
    AdminResponsesResponse,
)


def _vote_count():
    return (
        select(func.count(Vote.id))
        .where(or_(Vote.response_a_id == Response.id, Vote.response_b_id == Response.id))
        .correlate(Response)
        .scalar_subquery()
    )


def _to_item(response: Response, vote_count: int) -> AdminResponseItem:
    return AdminResponseItem(
        id=response.id,
        prompt_id=response.prompt_id,
        model=response.model,
        text=response.text,
        inference_metadata=response.inference_metadata,
        active=response.active,
        included_in_ranking=response.included_in_ranking,
        created_at=response.created_at,
        vote_count=vote_count,
    )


def _get_item(db: OrmSession, response_id: int) -> AdminResponseItem:
    row = db.execute(
        select(Response, _vote_count()).where(Response.id == response_id)
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Inferència no trobada")
    return _to_item(*row)


def list_responses(
    db: OrmSession,
    *,
    limit: int,
    offset: int,
    prompt_id: int | None,
    model: str | None,
    active: bool | None,
    included_in_ranking: bool | None,
) -> AdminResponsesResponse:
    """Retorna una pàgina d'inferències per ordre d'identificador, amb el recompte de vots."""
    filters = []
    if prompt_id is not None:
        filters.append(Response.prompt_id == prompt_id)
    if model is not None:
        filters.append(Response.model == model)
    if active is not None:
        filters.append(Response.active == active)
    if included_in_ranking is not None:
        filters.append(Response.included_in_ranking == included_in_ranking)

    rows = db.execute(
        select(Response, _vote_count())
        .where(*filters)
        .order_by(Response.id)
        .limit(limit)
        .offset(offset)
    ).all()
    total = db.scalar(select(func.count(Response.id)).where(*filters))
    return AdminResponsesResponse(
        total=total or 0, responses=[_to_item(response, count) for response, count in rows]
    )


def create_response(db: OrmSession, payload: AdminResponseCreate) -> AdminResponseItem:
    """Afegeix la resposta d'un model a un prompt; cada model hi respon una sola vegada."""
    if db.get(Prompt, payload.prompt_id) is None:
        raise HTTPException(status_code=404, detail="Prompt no trobat")

    response = Response(
        prompt_id=payload.prompt_id,
        model=payload.model,
        text=payload.text,
        inference_metadata=payload.inference_metadata,
    )
    db.add(response)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Aquest model ja té una inferència per a aquest prompt"
        ) from None
    return _get_item(db, response.id)


def update_response(
    db: OrmSession, response_id: int, payload: AdminResponsePatch
) -> AdminResponseItem:
    """Canvia si una inferència es mostra i si els seus vots compten al rànquing."""
    response = db.get(Response, response_id)
    if response is None:
        raise HTTPException(status_code=404, detail="Inferència no trobada")

    if payload.active is not None:
        response.active = payload.active
    if payload.included_in_ranking is not None:
        response.included_in_ranking = payload.included_in_ranking
    db.commit()
    return _get_item(db, response_id)


def delete_response(db: OrmSession, response_id: int) -> None:
    """Esborra una inferència que no té cap vot ni omissió associats."""
    response = db.get(Response, response_id)
    if response is None:
        raise HTTPException(status_code=404, detail="Inferència no trobada")

    referenced = db.scalar(
        select(Vote.id)
        .where(or_(Vote.response_a_id == response_id, Vote.response_b_id == response_id))
        .limit(1)
    ) or db.scalar(
        select(TaskSkip.id)
        .where(or_(TaskSkip.response_a_id == response_id, TaskSkip.response_b_id == response_id))
        .limit(1)
    )
    if referenced is not None:
        raise HTTPException(
            status_code=409,
            detail="La inferència té vots o omissions associats; desactiveu-la en lloc d'esborrar",
        )

    db.delete(response)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="La inferència encara està referenciada i no es pot esborrar"
        ) from None
