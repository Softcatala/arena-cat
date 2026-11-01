"""Endpoints d'administració, reservats als usuaris amb el rol d'administrador."""

from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.deps import CurrentAdmin, DbSession
from app.schemas import (
    AdminPromptCreate,
    AdminPromptPatch,
    AdminPromptResponse,
    AdminPromptsResponse,
    AdminResponseCreate,
    AdminResponseItem,
    AdminResponsePatch,
    AdminResponsesResponse,
    AdminUserResponse,
    AdminUsersResponse,
    ImportResponsesRequest,
    ImportResponsesResponse,
)
from app.services import (
    admin_import_service,
    admin_prompt_service,
    admin_response_service,
    admin_service,
)

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
    return admin_service.block_user(db, admin, user_id)


@router.post("/users/{user_id}/unblock")
def unblock_user(user_id: int, db: DbSession, _admin: CurrentAdmin) -> AdminUserResponse:
    """Desbloqueja un usuari, que podrà tornar a iniciar sessió."""
    return admin_service.unblock_user(db, user_id)


@router.get("/prompts")
def list_prompts(
    db: DbSession,
    _admin: CurrentAdmin,
    response: Response,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    version: str | None = None,
    category_code: str | None = None,
    active: bool | None = None,
) -> AdminPromptsResponse:
    """Llista els prompts per pàgines, amb el nombre d'inferències de cadascun."""
    response.headers["Cache-Control"] = "no-store"
    return admin_prompt_service.list_prompts(
        db,
        limit=limit,
        offset=offset,
        version=version,
        category_code=category_code,
        active=active,
    )


@router.post("/prompts", status_code=status.HTTP_201_CREATED)
def create_prompt(
    payload: AdminPromptCreate, db: DbSession, _admin: CurrentAdmin
) -> AdminPromptResponse:
    """Crea un prompt; el seu contingut no es pot repetir."""
    return admin_prompt_service.create_prompt(db, payload)


@router.patch("/prompts/{prompt_id}")
def update_prompt(
    prompt_id: int, payload: AdminPromptPatch, db: DbSession, _admin: CurrentAdmin
) -> AdminPromptResponse:
    """Activa o desactiva un prompt, sense esborrar-ne res."""
    return admin_prompt_service.update_prompt(db, prompt_id, payload)


@router.delete("/prompts/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prompt(prompt_id: int, db: DbSession, _admin: CurrentAdmin) -> None:
    """Esborra un prompt sense inferències associades."""
    admin_prompt_service.delete_prompt(db, prompt_id)


@router.get("/responses")
def list_responses(
    db: DbSession,
    _admin: CurrentAdmin,
    response: Response,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    prompt_id: int | None = None,
    model: str | None = None,
    active: bool | None = None,
    included_in_ranking: bool | None = None,
) -> AdminResponsesResponse:
    """Llista les inferències per pàgines, amb el nombre de vots de cadascuna."""
    response.headers["Cache-Control"] = "no-store"
    return admin_response_service.list_responses(
        db,
        limit=limit,
        offset=offset,
        prompt_id=prompt_id,
        model=model,
        active=active,
        included_in_ranking=included_in_ranking,
    )


@router.post("/responses", status_code=status.HTTP_201_CREATED)
def create_response(
    payload: AdminResponseCreate, db: DbSession, _admin: CurrentAdmin
) -> AdminResponseItem:
    """Afegeix la inferència d'un model a un prompt, activa i inclosa al rànquing."""
    return admin_response_service.create_response(db, payload)


@router.post("/responses/import")
def import_responses(
    payload: ImportResponsesRequest, db: DbSession, _admin: CurrentAdmin
) -> ImportResponsesResponse:
    """Importa inferències dels fitxers YAML de la canonada; cada fitxer és independent."""
    return admin_import_service.import_responses(db, payload)


@router.patch("/responses/{response_id}")
def update_response(
    response_id: int, payload: AdminResponsePatch, db: DbSession, _admin: CurrentAdmin
) -> AdminResponseItem:
    """Activa o desactiva una inferència, o la inclou o exclou del rànquing."""
    return admin_response_service.update_response(db, response_id, payload)


@router.delete("/responses/{response_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_response(response_id: int, db: DbSession, _admin: CurrentAdmin) -> None:
    """Esborra una inferència sense vots ni omissions."""
    admin_response_service.delete_response(db, response_id)
