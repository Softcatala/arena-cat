"""Endpoints d'administració, reservats als usuaris amb el rol d'administrador."""

from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.deps import CurrentAdmin, DbSession
from app.schemas import (
    AdminPromptCreate,
    AdminPromptResponse,
    AdminPromptsResponse,
    AdminUserResponse,
    AdminUsersResponse,
)
from app.services import admin_prompt_service, admin_service

router = APIRouter()


@router.get("/users")
def list_users(
    db: DbSession,
    _admin: CurrentAdmin,
    response: Response,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AdminUsersResponse:
    """Llista els usuaris per pàgines, sense contrasenyes ni tokens."""
    response.headers["Cache-Control"] = "no-store"
    return admin_service.list_users(db, limit=limit, offset=offset)


@router.post("/users/{user_id}/block")
def block_user(user_id: int, db: DbSession, admin: CurrentAdmin) -> AdminUserResponse:
    """Bloqueja un usuari: no pot entrar i perd les sessions obertes."""
    return AdminUserResponse.model_validate(admin_service.block_user(db, admin, user_id))


@router.post("/users/{user_id}/unblock")
def unblock_user(user_id: int, db: DbSession, _admin: CurrentAdmin) -> AdminUserResponse:
    """Desbloqueja un usuari, que podrà tornar a iniciar sessió."""
    return AdminUserResponse.model_validate(admin_service.unblock_user(db, user_id))


@router.get("/prompts")
def list_prompts(
    db: DbSession,
    _admin: CurrentAdmin,
    response: Response,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    version: str | None = None,
    category_code: str | None = None,
) -> AdminPromptsResponse:
    """Llista els prompts per pàgines, amb el nombre d'inferències de cadascun."""
    response.headers["Cache-Control"] = "no-store"
    return admin_prompt_service.list_prompts(
        db, limit=limit, offset=offset, version=version, category_code=category_code
    )


@router.post("/prompts", status_code=status.HTTP_201_CREATED)
def create_prompt(
    payload: AdminPromptCreate, db: DbSession, _admin: CurrentAdmin
) -> AdminPromptResponse:
    """Crea un prompt; el seu contingut no es pot repetir."""
    return admin_prompt_service.create_prompt(db, payload)


@router.delete("/prompts/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prompt(prompt_id: int, db: DbSession, _admin: CurrentAdmin) -> None:
    """Esborra un prompt sense inferències associades."""
    admin_prompt_service.delete_prompt(db, prompt_id)
