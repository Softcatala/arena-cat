from datetime import UTC, datetime

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.db import get_db
from app.models import Session as UserSession
from app.models import User
from app.security import hash_session_token


def get_current_verified_user(
    session_token: str | None = Cookie(None),
    db: OrmSession = Depends(get_db),
) -> User:
    """Retorna l'usuari autenticat i verificat a partir de la cookie de sessió."""
    if session_token is None:
        raise HTTPException(status_code=401, detail="Sessió invàlida o caducada")

    token_hash = hash_session_token(session_token)
    now = datetime.now(UTC)

    active_session = db.scalar(
        select(UserSession).where(
            UserSession.token_hash == token_hash,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
        )
    )
    if active_session is None:
        raise HTTPException(status_code=401, detail="Sessió invàlida o caducada")

    user = db.get(User, active_session.user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(status_code=401, detail="Sessió invàlida o caducada")

    if user.email_verified_at is None:
        raise HTTPException(status_code=403, detail="Cal verificar l'email per continuar")

    return user
