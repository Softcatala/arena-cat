"""Política de contrasenya de les contrasenyes noves: 8–128 caràcters, una majúscula i un número.

S'aplica a l'alta i al restabliment. No s'aplica a l'entrada: qui ja té un compte ha de
poder entrar amb la contrasenya que va triar.
"""

import re
from urllib.parse import unquote

import pytest

from tests.conftest import DEFAULT_PASSWORD

VALID_PASSWORDS = [
    "Abcdefg1",  # justament 8 caràcters
    "abcdefG1abc",  # la majúscula i el número no cal que siguin al principi
    "Àbcdefg1",  # majúscula accentuada
    "Contrasenya-Segura-123",
    "A" + "b" * 126 + "1",  # justament 128 caràcters
]

INVALID_PASSWORDS = {
    "sense majúscula": "abcdefg1",
    "sense número": "Abcdefgh",
    "sense majúscula ni número": "abcdefgh",
    "només majúscules i lletres": "ABCDEFGHIJ",
}


def _register(client, email: str, password: str):
    return client.post(
        "/api/auth/register", json={"email": email, "password": password, "consent": True}
    )


def _reset(client, token: str, password: str):
    return client.post("/api/auth/reset-password", json={"token": token, "new_password": password})


def _token_from(message) -> str:
    match = re.search(r"/reset-password\?token=(\S+)", message.get_content())
    assert match is not None
    return unquote(match.group(1))


def _first_error(response) -> dict:
    return response.json()["detail"][0]


@pytest.mark.parametrize("password", VALID_PASSWORDS)
def test_register_accepts_a_password_that_meets_the_policy(client, password):
    response = _register(client, "valida@example.com", password)

    assert response.status_code == 200


@pytest.mark.parametrize("password", INVALID_PASSWORDS.values(), ids=INVALID_PASSWORDS.keys())
def test_register_rejects_a_password_without_a_capital_letter_and_a_number(client, password):
    response = _register(client, "invalida@example.com", password)

    assert response.status_code == 422
    assert _first_error(response)["type"] == "password_policy"


def test_register_still_rejects_a_password_that_is_too_short_or_too_long(client):
    short = _register(client, "curta@example.com", "Abcde1")
    long = _register(client, "llarga@example.com", "A1" + "b" * 127)

    assert short.status_code == long.status_code == 422
    assert _first_error(short)["type"] == "string_too_short"
    assert _first_error(long)["type"] == "string_too_long"


def test_register_does_not_create_the_account_when_the_password_is_rejected(client, session):
    from sqlalchemy import select

    from app.models import User

    _register(client, "no_creat@example.com", "abcdefg1")

    assert session.scalar(select(User).where(User.email == "no_creat@example.com")) is None


@pytest.mark.parametrize("password", VALID_PASSWORDS)
def test_reset_password_accepts_a_password_that_meets_the_policy(
    client, create_user, outbox, password
):
    create_user("reset_valida@example.com")
    client.post("/api/auth/forgot-password", json={"email": "reset_valida@example.com"})

    response = _reset(client, _token_from(outbox[0]), password)

    assert response.status_code == 200


@pytest.mark.parametrize("password", INVALID_PASSWORDS.values(), ids=INVALID_PASSWORDS.keys())
def test_reset_password_rejects_a_password_without_a_capital_letter_and_a_number(
    client, create_user, outbox, password
):
    create_user("reset_invalida@example.com")
    client.post("/api/auth/forgot-password", json={"email": "reset_invalida@example.com"})

    response = _reset(client, _token_from(outbox[0]), password)

    assert response.status_code == 422
    assert _first_error(response)["type"] == "password_policy"


def test_a_rejected_new_password_does_not_spend_the_reset_link(client, create_user, outbox):
    """Qui s'equivoca en triar la contrasenya pot tornar-ho a provar amb el mateix enllaç."""
    create_user("reintent@example.com")
    client.post("/api/auth/forgot-password", json={"email": "reintent@example.com"})
    token = _token_from(outbox[0])

    weak = _reset(client, token, "abcdefg1")
    strong = _reset(client, token, "NovaContrasenya456!")

    assert weak.status_code == 422
    assert strong.status_code == 200


def test_login_is_not_subject_to_the_policy(client, create_user):
    """Un compte antic amb una contrasenya que no compleix la política ha de poder entrar."""
    create_user("antic@example.com", password="contrasenya-antiga")

    response = client.post(
        "/api/auth/login", json={"email": "antic@example.com", "password": "contrasenya-antiga"}
    )

    assert response.status_code == 200


def test_the_default_test_password_meets_the_policy(client):
    assert _register(client, "per_defecte@example.com", DEFAULT_PASSWORD).status_code == 200
