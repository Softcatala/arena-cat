"""Un restabliment de contrasenya no pot deixar viva una sessió oberta amb la contrasenya antiga.

Cada test força una de les dues intercalacions possibles entre l'entrada (que valida la
contrasenya i després insereix la sessió) i el restabliment (que canvia el hash i revoca les
sessions).
"""

import threading
import time
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session as OrmSession

from app.models import Session, User
from app.schemas import LoginRequest, ResetPasswordRequest
from app.security import (
    compute_email_hash,
    create_password_reset_token,
    hash_password,
)
from app.services import auth_service
from tests.conftest import DEFAULT_PASSWORD

NEW_PASSWORD = "NovaContrasenya456!"


def test_login_fails_if_the_password_is_reset_after_it_was_checked(
    session, create_user, monkeypatch
):
    """El restabliment acaba entre la validació de la contrasenya i la inserció de la sessió."""
    user = create_user("carrera_previa@example.com")
    reset = ResetPasswordRequest(
        token=create_password_reset_token(user.id, user.password_hash),
        new_password=NEW_PASSWORD,
    )
    verify_password = auth_service.verify_password

    def verify_then_reset(password, password_hash):
        valid = verify_password(password, password_hash)
        auth_service.reset_password(session, reset)
        return valid

    monkeypatch.setattr(auth_service, "verify_password", verify_then_reset)

    with pytest.raises(HTTPException) as error:
        auth_service.login_user(
            session, LoginRequest(email="carrera_previa@example.com", password=DEFAULT_PASSWORD)
        )

    assert error.value.status_code == 401
    assert session.scalars(select(Session).where(Session.revoked_at.is_(None))).all() == []


def test_reset_revokes_a_session_that_a_concurrent_login_is_creating(engine, monkeypatch):
    """El restabliment arriba quan l'entrada ja ha validat la contrasenya i té la sessió a mig fer.

    Amb dues connexions reals: si l'entrada no reservés la fila de l'usuari, el restabliment
    no esperaria, no veuria encara la sessió i la deixaria viva.
    """
    with OrmSession(engine) as setup:
        user = User(
            email="carrera_concurrent@example.com",
            email_hash=compute_email_hash("carrera_concurrent@example.com"),
            password_hash=hash_password(DEFAULT_PASSWORD),
            consent_version="v1",
            consent_at=datetime.now(UTC),
            email_verified_at=datetime.now(UTC),
        )
        setup.add(user)
        setup.commit()
        user_id, password_hash = user.id, user.password_hash

    login_holds_the_lock = threading.Event()
    new_session_token = auth_service.new_session_token

    def slow_new_session_token():
        # S'arriba aquí un cop l'entrada ha validat la contrasenya i ha reservat la fila.
        login_holds_the_lock.set()
        time.sleep(1)
        return new_session_token()

    monkeypatch.setattr(auth_service, "new_session_token", slow_new_session_token)

    def do_login():
        with OrmSession(engine) as db:
            auth_service.login_user(
                db,
                LoginRequest(email="carrera_concurrent@example.com", password=DEFAULT_PASSWORD),
            )

    try:
        login = threading.Thread(target=do_login)
        login.start()
        assert login_holds_the_lock.wait(timeout=10)

        with OrmSession(engine) as db:
            auth_service.reset_password(
                db,
                ResetPasswordRequest(
                    token=create_password_reset_token(user_id, password_hash),
                    new_password=NEW_PASSWORD,
                ),
            )
        login.join(timeout=10)

        with OrmSession(engine) as check:
            sessions = check.scalars(select(Session).where(Session.user_id == user_id)).all()
            assert len(sessions) == 1
            assert sessions[0].revoked_at is not None
    finally:
        with OrmSession(engine) as cleanup:
            cleanup.execute(delete(Session).where(Session.user_id == user_id))
            cleanup.execute(delete(User).where(User.id == user_id))
            cleanup.commit()
