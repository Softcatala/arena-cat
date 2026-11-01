"""Endpoints d'administració, reservats als usuaris amb el rol d'administrador."""

from typing import Annotated

from fastapi import APIRouter, Query, Response

from app.deps import CurrentAdmin, DbSession
from app.schemas import AdminUserResponse, AdminUsersResponse
from app.services import admin_service

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
