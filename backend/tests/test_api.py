from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import get_db
from app.main import app
from app.models import Category, Prompt, Response, Session, User, Vote, Winner
from app.security import (
    compute_email_hash,
    create_email_verification_token,
    create_task_token,
    hash_password,
    hash_session_token,
)


# Creem una fixture pels tests i passem 'session' com a
# paràmetre perquè utilitzi la base de dades de conftest.py.
@pytest.fixture
def client(session):
    # Sobreescrivim la dependència 'get_db' de FastAPI perquè utilitzi la 'session' de test.
    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    # Retornem el TestClient.
    with TestClient(app) as test_client:
        yield test_client

    # Netejem el override.
    app.dependency_overrides.clear()


def test_get_task_empty_db(client):
    """Prova què passa si demanem una tasca quan la db està buida."""
    # Fem la petició GET a la API
    response = client.get(
        "/api/task", params={"category_code": "correccio", "session_id": "test_session_id"}
    )

    # Comprovem el status code
    assert response.status_code == 404

    # Comprovem el missatge
    assert response.json()["detail"] == "No hi ha tasques disponibles o bé les has realitzat totes."


def test_get_task_with_data(client, session):
    """Prova què passa quan hi ha dades a la db."""
    # Inserim una categoria de prova
    c = Category(code="test_cat", name="Categoria de prova")
    session.add(c)
    session.commit()

    # Inserim dades falses
    p = Prompt(version="v1", code="test_p", category_id=c.id, text="El gat es blau")
    session.add(p)
    session.commit()

    r1 = Response(prompt_id=p.id, model="model_1", text="El gat és blau")
    r2 = Response(prompt_id=p.id, model="model_2", text="El gat es color blau")
    session.add_all([r1, r2])
    session.commit()

    # Fem la petició GET a la API
    response = client.get(
        "/api/task", params={"category_code": "test_cat", "session_id": "test_session_id"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["prompt"] == "El gat es blau"
    assert "token" in data


def test_post_vote_invalid_token(client):
    """Prova d'enviar un vot amb un token inventat."""
    response = client.post("/api/vote", json={"winner": "a", "token": "inventat"})
    assert response.status_code == 401


def test_post_vote_success(client, session):
    """Prova què passa quan enviem un vot vàlid i sencer."""
    # Preparem la db
    p = Prompt(version="v1", code="test_p2", category_id=1, text="Bon dia")
    session.add(p)
    session.commit()
    r1 = Response(prompt_id=p.id, model="model_A", text="Hola")
    r2 = Response(prompt_id=p.id, model="model_B", text="Bon dia")
    session.add_all([r1, r2])
    session.commit()

    token = create_task_token(p.id, r1.id, r2.id, session_id="test_session_id")

    # Enviem el vot amb el token
    response = client.post("/api/vote", json={"winner": "a", "token": token})
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_user_success(client, session):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "nou_usuari@example.com",
            "password": "ContrasenyaSegura123!",
            "consent": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "pending_verification"

    created_user = session.scalar(select(User).where(User.email == "nou_usuari@example.com"))
    assert created_user is not None
    assert created_user.email_hash == compute_email_hash("nou_usuari@example.com")
    assert created_user.password_hash.startswith("$argon2id$")
    assert created_user.consent_at is not None


def test_register_requires_explicit_consent(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "sense_consent@example.com",
            "password": "ContrasenyaSegura123!",
            "consent": False,
        },
    )

    assert response.status_code == 400


def test_register_detects_reregistration_after_deletion(client, session):
    old_user = User(
        email="antic@example.com",
        email_hash=compute_email_hash("antic@example.com"),
        password_hash=hash_password("ContrasenyaVella123!"),
        consent_version="v1",
        consent_at=datetime.now(UTC),
    )
    session.add(old_user)
    session.flush()
    # Marquem la baixa mantenint l'email_hash per detectar re-registres.
    old_user.deleted_at = datetime.now(UTC)
    old_user.consent_at = datetime.now(UTC)
    session.add(old_user)
    session.commit()

    response = client.post(
        "/api/auth/register",
        json={
            "email": "antic@example.com",
            "password": "ContrasenyaNova123!",
            "consent": True,
        },
    )

    assert response.status_code == 409


def test_verify_email_success(client, session):
    user = User(
        email="verificar@example.com",
        email_hash=compute_email_hash("verificar@example.com"),
        password_hash=hash_password("ContrasenyaSegura123!"),
        consent_version="v1",
        consent_at=datetime.now(UTC),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    token = create_email_verification_token(user.id, user.email)
    response = client.post("/api/auth/verify", json={"token": token})

    assert response.status_code == 200
    assert response.json()["status"] == "verified"

    session.refresh(user)
    assert user.email_verified_at is not None


def test_login_success_sets_cookie_and_creates_session(client, session):
    user = User(
        email="login_ok@example.com",
        email_hash=compute_email_hash("login_ok@example.com"),
        password_hash=hash_password("ContrasenyaSegura123!"),
        consent_version="v1",
        consent_at=datetime.now(UTC),
        email_verified_at=datetime.now(UTC),
    )
    session.add(user)
    session.commit()

    response = client.post(
        "/api/auth/login",
        json={"email": "login_ok@example.com", "password": "ContrasenyaSegura123!"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "logged_in"
    assert "session_token" in response.cookies

    token_hash = hash_session_token(response.cookies["session_token"])
    stored_session = session.scalar(select(Session).where(Session.token_hash == token_hash))
    assert stored_session is not None
    assert stored_session.user_id == user.id
    assert stored_session.revoked_at is None


def test_login_requires_verified_email(client, session):
    user = User(
        email="login_unverified@example.com",
        email_hash=compute_email_hash("login_unverified@example.com"),
        password_hash=hash_password("ContrasenyaSegura123!"),
        consent_version="v1",
        consent_at=datetime.now(UTC),
    )
    session.add(user)
    session.commit()

    response = client.post(
        "/api/auth/login",
        json={"email": "login_unverified@example.com", "password": "ContrasenyaSegura123!"},
    )

    assert response.status_code == 403


def test_logout_revokes_session_and_clears_cookie(client, session):
    user = User(
        email="logout_ok@example.com",
        email_hash=compute_email_hash("logout_ok@example.com"),
        password_hash=hash_password("ContrasenyaSegura123!"),
        consent_version="v1",
        consent_at=datetime.now(UTC),
        email_verified_at=datetime.now(UTC),
    )
    session.add(user)
    session.commit()

    login_response = client.post(
        "/api/auth/login",
        json={"email": "logout_ok@example.com", "password": "ContrasenyaSegura123!"},
    )
    assert login_response.status_code == 200
    raw_token = login_response.cookies.get("session_token")
    assert raw_token is not None

    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 200
    assert logout_response.json()["status"] == "logged_out"

    token_hash = hash_session_token(raw_token)
    stored_session = session.scalar(select(Session).where(Session.token_hash == token_hash))
    assert stored_session is not None
    assert stored_session.revoked_at is not None


def test_logout_without_cookie_returns_logged_out(client, session):
    response = client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.json()["status"] == "logged_out"
    assert session.scalar(select(Session)) is None


def test_delete_account_success_anonymizes_and_revokes_sessions(client, session):
    user = User(
        email="delete_ok@example.com",
        email_hash=compute_email_hash("delete_ok@example.com"),
        password_hash=hash_password("ContrasenyaSegura123!"),
        consent_version="v1",
        consent_at=datetime.now(UTC),
        email_verified_at=datetime.now(UTC),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    original_email_hash = user.email_hash

    login_response = client.post(
        "/api/auth/login",
        json={"email": "delete_ok@example.com", "password": "ContrasenyaSegura123!"},
    )
    assert login_response.status_code == 200

    response = client.post(
        "/api/auth/delete-account",
        json={"current_password": "ContrasenyaSegura123!"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "deleted"

    session.refresh(user)
    assert user.email is None
    assert user.password_hash is None
    assert user.email_verified_at is None
    assert user.consent_at is None
    assert user.deleted_at is not None
    assert user.email_hash == original_email_hash

    user_sessions = session.scalars(select(Session).where(Session.user_id == user.id)).all()
    assert len(user_sessions) > 0
    assert all(s.revoked_at is not None for s in user_sessions)

    reregister_response = client.post(
        "/api/auth/register",
        json={
            "email": "delete_ok@example.com",
            "password": "ContrasenyaNova123!",
            "consent": True,
        },
    )
    assert reregister_response.status_code == 409


def test_delete_account_requires_session(client):
    response = client.post(
        "/api/auth/delete-account",
        json={"current_password": "ContrasenyaSegura123!"},
    )

    assert response.status_code == 401


def test_delete_account_requires_correct_password(client, session):
    user = User(
        email="delete_wrong_pass@example.com",
        email_hash=compute_email_hash("delete_wrong_pass@example.com"),
        password_hash=hash_password("ContrasenyaSegura123!"),
        consent_version="v1",
        consent_at=datetime.now(UTC),
        email_verified_at=datetime.now(UTC),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    login_response = client.post(
        "/api/auth/login",
        json={"email": "delete_wrong_pass@example.com", "password": "ContrasenyaSegura123!"},
    )
    assert login_response.status_code == 200

    response = client.post(
        "/api/auth/delete-account",
        json={"current_password": "contrasenya_incorrecta"},
    )

    assert response.status_code == 401

    session.refresh(user)
    assert user.deleted_at is None
    assert user.email == "delete_wrong_pass@example.com"
    assert user.password_hash is not None


def test_export_data_returns_user_and_votes(client, session):
    user = User(
        email="export_ok@example.com",
        email_hash=compute_email_hash("export_ok@example.com"),
        password_hash=hash_password("ContrasenyaSegura123!"),
        consent_version="v1",
        consent_at=datetime.now(UTC),
        email_verified_at=datetime.now(UTC),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    category = Category(code="export_cat", name="Categoria export")
    session.add(category)
    session.commit()

    prompt = Prompt(version="v1", code="export_prompt", category_id=category.id, text="Text prova")
    session.add(prompt)
    session.commit()

    response_a = Response(prompt_id=prompt.id, model="model_A", text="Resposta A")
    response_b = Response(prompt_id=prompt.id, model="model_B", text="Resposta B")
    session.add_all([response_a, response_b])
    session.commit()

    vote = Vote(
        prompt_id=prompt.id,
        user_id=user.id,
        response_a_id=response_a.id,
        response_b_id=response_b.id,
        winner=Winner.a,
        session_id="sessio_export_1",
    )
    session.add(vote)
    session.commit()

    login_response = client.post(
        "/api/auth/login",
        json={"email": "export_ok@example.com", "password": "ContrasenyaSegura123!"},
    )
    assert login_response.status_code == 200

    response = client.get("/api/auth/export")
    assert response.status_code == 200

    data = response.json()
    assert data["user"]["id"] == user.id
    assert data["user"]["email"] == "export_ok@example.com"
    assert data["user"]["consent_version"] == "v1"

    assert len(data["votes"]) == 1
    assert data["votes"][0]["prompt_id"] == prompt.id
    assert data["votes"][0]["response_a_id"] == response_a.id
    assert data["votes"][0]["response_b_id"] == response_b.id
    assert data["votes"][0]["winner"] == "a"


def test_export_data_requires_session(client):
    response = client.get("/api/auth/export")

    assert response.status_code == 401
