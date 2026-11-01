"""Operacions d'administració sobre els usuaris."""

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session as OrmSession

from app.models import Session, TaskSkip, User, Vote
from app.schemas import AdminUserResponse, AdminUsersResponse


def _last_activity():
    """Expressió amb la darrera activitat de l'usuari: sessió, vot o omissió.

    `GREATEST` ignora els nuls, així que només és nul si l'usuari no ha fet res.
    """
    return func.greatest(
        *(
            select(func.max(table.created_at))
            .where(table.user_id == User.id)
            .correlate(User)
            .scalar_subquery()
            for table in (Session, Vote, TaskSkip)
        )
    )


def _to_response(user: User, last_activity_at: datetime | None) -> AdminUserResponse:
    response = AdminUserResponse.model_validate(user)
    response.last_activity_at = last_activity_at
    return response


def _get_response(db: OrmSession, user_id: int) -> AdminUserResponse:
    user, last_activity_at = db.execute(
        select(User, _last_activity()).where(User.id == user_id)
    ).one()
    return _to_response(user, last_activity_at)


def list_users(db: OrmSession, *, limit: int, offset: int) -> AdminUsersResponse:
    """Retorna una pàgina d'usuaris per ordre d'identificador, amb el total."""
    rows = db.execute(
        select(User, _last_activity()).order_by(User.id).limit(limit).offset(offset)
    ).all()
    total = db.scalar(select(func.count()).select_from(User)) or 0
    return AdminUsersResponse(
        total=total, users=[_to_response(user, activity) for user, activity in rows]
    )


def _get_active_user(db: OrmSession, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuari no trobat")
    if user.deleted_at is not None:
        raise HTTPException(status_code=409, detail="El compte ja s'ha donat de baixa")
    return user


def block_user(db: OrmSession, admin: User, user_id: int) -> AdminUserResponse:
    """Bloqueja un usuari i revoca totes les seves sessions obertes.

    És idempotent: si ja estava bloquejat, conserva la data original.
    """
    if admin.id == user_id:
        raise HTTPException(status_code=409, detail="No et pots bloquejar a tu mateix")

    user = _get_active_user(db, user_id)
    now = datetime.now(UTC)
    if user.blocked_at is None:
        user.blocked_at = now
    db.execute(
        update(Session)
        .where(Session.user_id == user.id, Session.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    db.commit()
    return _get_response(db, user.id)


def unblock_user(db: OrmSession, user_id: int) -> AdminUserResponse:
    """Treu el bloqueig d'un usuari; les sessions revocades no es recuperen."""
    user = _get_active_user(db, user_id)
    user.blocked_at = None
    db.commit()
    return _get_response(db, user.id)
