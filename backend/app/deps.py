"""Dependències d'autenticació reutilitzables per als endpoints de FastAPI.

Exposa àlies `Annotated` per injectar la sessió de base de dades i l'usuari
autenticat (verificat o no) directament a la signatura dels handlers.
"""

from typing import Annotated

from fastapi import Cookie, Depends
from sqlalchemy.orm import Session as OrmSession

from app.config import get_settings
from app.db import get_db
from app.models import User
from app.services import auth_service

DbSession = Annotated[OrmSession, Depends(get_db)]
SessionCookie = Annotated[str | None, Cookie(alias=get_settings().cookie_name)]


def get_current_user(db: DbSession, session_token: SessionCookie = None) -> User:
    """Retorna l'usuari autenticat a partir de la cookie de sessió."""
    return auth_service.resolve_session_user(db, session_token)


def get_current_verified_user(db: DbSession, session_token: SessionCookie = None) -> User:
    """Retorna l'usuari autenticat exigint que tingui l'email verificat."""
    return auth_service.resolve_session_user(db, session_token, require_verified=True)


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentVerifiedUser = Annotated[User, Depends(get_current_verified_user)]
