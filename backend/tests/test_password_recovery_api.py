"""Tests de la recuperació de contrasenya: sol·licitud del correu i canvi de contrasenya."""

import re
import smtplib
from datetime import UTC, datetime, timedelta
from urllib.parse import unquote

import pytest
from sqlalchemy import select

from app import security
from app.config import get_settings
from app.models import Session
from app.security import (
    create_email_verification_token,
    create_password_reset_token,
    hash_password,
    password_fingerprint,
    verify_password_reset_token,
)
from app.services import email_service
from app.services.auth_service import anonymize_user_rgpd
from tests.conftest import DEFAULT_PASSWORD

NEW_PASSWORD = "NovaContrasenya456!"


@pytest.fixture
def require_email_verification(monkeypatch):
    monkeypatch.setenv("REQUIRE_EMAIL_VERIFICATION", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _forgot(client, email: str):
    return client.post("/api/auth/forgot-password", json={"email": email})


def _reset(client, token: str, password: str = NEW_PASSWORD):
    return client.post("/api/auth/reset-password", json={"token": token, "new_password": password})


def _login(client, email: str, password: str):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _token_from(message) -> str:
    """Extreu el token de l'enllaç de restabliment d'un correu enviat."""
    match = re.search(r"/reset-password\?token=(\S+)", message.get_content())
    assert match is not None
    return unquote(match.group(1))


# --- Sol·licitud del correu ---------------------------------------------------------------


def test_forgot_password_sends_a_reset_link_to_a_verified_user(
    client, session, create_user, outbox
):
    user = create_user("oblidada@example.com")

    response = _forgot(client, "oblidada@example.com")

    assert response.status_code == 200
    assert response.json() == {"status": "requested"}
    (message,) = outbox
    assert message["To"] == "oblidada@example.com"
    payload = verify_password_reset_token(_token_from(message))
    assert payload["user_id"] == str(user.id)
    assert payload["pwd"] == password_fingerprint(user.password_hash)
    session.refresh(user)
    assert user.password_reset_sent_at is not None


def test_forgot_password_answers_the_same_for_unknown_and_known_emails(client, create_user, outbox):
    create_user("existent@example.com")

    known = _forgot(client, "existent@example.com")
    unknown = _forgot(client, "no_existeix@example.com")

    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    assert [message["To"] for message in outbox] == ["existent@example.com"]


def test_forgot_password_sends_nothing_to_an_unverified_account_when_verification_is_required(
    client, create_user, outbox, require_email_verification
):
    create_user("sense_verificar@example.com", verified=False)

    response = _forgot(client, "sense_verificar@example.com")

    assert response.status_code == 200
    assert outbox == []


def test_forgot_password_works_for_any_account_when_verification_is_not_required(
    client, create_user, outbox
):
    create_user("verificacio_opcional@example.com", verified=False)

    _forgot(client, "verificacio_opcional@example.com")

    assert len(outbox) == 1


def test_forgot_password_sends_nothing_to_a_deleted_account(client, session, create_user, outbox):
    user = create_user("baixa@example.com")
    anonymize_user_rgpd(user, datetime.now(UTC))
    session.commit()

    response = _forgot(client, "baixa@example.com")

    assert response.status_code == 200
    assert outbox == []


def test_forgot_password_is_silently_limited_by_a_cooldown(client, create_user, outbox):
    create_user("massa_rapid@example.com")

    first = _forgot(client, "massa_rapid@example.com")
    second = _forgot(client, "massa_rapid@example.com")

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert len(outbox) == 1


def test_forgot_password_works_again_once_the_cooldown_has_passed(
    client, session, create_user, outbox
):
    user = create_user("passat_el_temps@example.com")
    user.password_reset_sent_at = datetime.now(UTC) - timedelta(minutes=2)
    session.commit()

    _forgot(client, "passat_el_temps@example.com")

    assert len(outbox) == 1


def test_forgot_password_does_not_share_the_cooldown_with_email_verification(
    client, session, create_user, outbox
):
    user = create_user("dos_cooldowns@example.com")
    user.verification_sent_at = datetime.now(UTC)
    session.commit()

    _forgot(client, "dos_cooldowns@example.com")

    assert len(outbox) == 1


def test_forgot_password_rejects_a_malformed_email(client, outbox):
    response = _forgot(client, "no-es-un-correu")

    assert response.status_code == 422
    assert outbox == []


def test_forgot_password_succeeds_even_if_the_mail_server_fails(client, create_user, monkeypatch):
    create_user("smtp_caigut@example.com")

    def broken_send(message):
        raise smtplib.SMTPException("servidor caigut")

    monkeypatch.setattr(email_service, "send_email", broken_send)

    response = _forgot(client, "smtp_caigut@example.com")

    assert response.status_code == 200


# --- Canvi de contrasenya -----------------------------------------------------------------


def test_reset_password_changes_the_password(client, create_user, outbox):
    create_user("canvi@example.com")
    _forgot(client, "canvi@example.com")

    response = _reset(client, _token_from(outbox[0]))

    assert response.status_code == 200
    assert response.json() == {"status": "password_reset"}
    assert _login(client, "canvi@example.com", NEW_PASSWORD).status_code == 200


def test_reset_password_stops_the_old_password_from_working(client, create_user, outbox):
    create_user("vella@example.com")
    _forgot(client, "vella@example.com")

    _reset(client, _token_from(outbox[0]))

    assert _login(client, "vella@example.com", DEFAULT_PASSWORD).status_code == 401


def test_reset_password_does_not_log_the_user_in(client, create_user, outbox):
    create_user("sense_sessio@example.com")
    _forgot(client, "sense_sessio@example.com")

    response = _reset(client, _token_from(outbox[0]))

    assert "session_token" not in response.cookies
    assert client.get("/api/auth/session").json()["authenticated"] is False


def test_reset_password_revokes_existing_sessions(client, session, create_user, login, outbox):
    user = create_user("sessions@example.com")
    login("sessions@example.com")
    assert client.get("/api/auth/session").json()["authenticated"] is True
    _forgot(client, "sessions@example.com")

    _reset(client, _token_from(outbox[0]))

    assert client.get("/api/auth/session").json()["authenticated"] is False
    stored = session.scalars(select(Session).where(Session.user_id == user.id)).all()
    assert stored
    assert all(item.revoked_at is not None for item in stored)


def test_reset_token_can_only_be_used_once(client, create_user, outbox):
    create_user("un_sol_us@example.com")
    _forgot(client, "un_sol_us@example.com")
    token = _token_from(outbox[0])

    first = _reset(client, token)
    second = _reset(client, token, "AltraContrasenya789!")

    assert first.status_code == 200
    assert second.status_code == 400
    assert _login(client, "un_sol_us@example.com", NEW_PASSWORD).status_code == 200


def test_reset_token_stops_working_if_the_password_changed_another_way(
    client, session, create_user
):
    user = create_user("canviada_abans@example.com")
    token = create_password_reset_token(user.id, user.password_hash)
    user.password_hash = hash_password("ContrasenyaCanviadaAbans1!")
    session.commit()

    response = _reset(client, token)

    assert response.status_code == 400


def test_reset_password_rejects_an_invalid_token(client, outbox):
    assert _reset(client, "no.token").status_code == 400


def test_reset_password_rejects_an_email_verification_token(client, create_user):
    user = create_user("token_equivocat@example.com")

    response = _reset(client, create_email_verification_token(user.id, user.email))

    assert response.status_code == 400


def test_reset_password_rejects_an_expired_token(client, create_user, monkeypatch):
    user = create_user("caducat@example.com")
    monkeypatch.setattr(security, "PASSWORD_RESET_TTL_MINUTES", -1)
    token = create_password_reset_token(user.id, user.password_hash)

    assert _reset(client, token).status_code == 400


def test_reset_password_rejects_a_deleted_account(client, session, create_user):
    user = create_user("esborrat@example.com")
    token = create_password_reset_token(user.id, user.password_hash)
    anonymize_user_rgpd(user, datetime.now(UTC))
    session.commit()

    assert _reset(client, token).status_code == 400


@pytest.mark.parametrize("password", ["curta", "x" * 129])
def test_reset_password_rejects_a_password_outside_the_allowed_length(
    client, create_user, outbox, password
):
    create_user("longitud@example.com")
    _forgot(client, "longitud@example.com")

    response = _reset(client, _token_from(outbox[0]), password)

    assert response.status_code == 422
    assert _login(client, "longitud@example.com", DEFAULT_PASSWORD).status_code == 200
