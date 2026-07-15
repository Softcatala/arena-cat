from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.models import Category, Prompt, Response, Session, User, Vote, Winner
from app.security import (
    compute_email_hash,
    create_email_verification_token,
    hash_password,
    hash_session_token,
)
from tests.conftest import DEFAULT_PASSWORD


@pytest.fixture
def require_email_verification(monkeypatch):
    monkeypatch.setenv("REQUIRE_EMAIL_VERIFICATION", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_register_user_success(client, session):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "nou_usuari@example.com",
            "password": DEFAULT_PASSWORD,
            "consent": True,
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "verified"}

    created_user = session.scalar(select(User).where(User.email == "nou_usuari@example.com"))
    assert created_user is not None
    assert created_user.email_hash == compute_email_hash("nou_usuari@example.com")
    assert created_user.password_hash.startswith("$argon2id$")
    assert created_user.consent_at is not None
    assert created_user.email_verified_at is not None


def test_register_requires_email_verification_when_enabled(
    client, session, require_email_verification
):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "verificacio_obligatoria@example.com",
            "password": DEFAULT_PASSWORD,
            "consent": True,
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "pending_verification"}

    created_user = session.scalar(
        select(User).where(User.email == "verificacio_obligatoria@example.com")
    )
    assert created_user is not None
    assert created_user.email_verified_at is None


def test_register_requires_explicit_consent(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "sense_consent@example.com",
            "password": DEFAULT_PASSWORD,
            "consent": False,
        },
    )

    assert response.status_code == 400


def test_register_rejects_invalid_email(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "no-es-un-email",
            "password": DEFAULT_PASSWORD,
            "consent": True,
        },
    )

    assert response.status_code == 422


def test_register_rejects_short_password(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "curta@example.com",
            "password": "curt",
            "consent": True,
        },
    )

    assert response.status_code == 422


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


def test_verify_email_success(client, session, create_user):
    user = create_user("verificar@example.com", verified=False)

    token = create_email_verification_token(user.id, user.email)
    response = client.post("/api/auth/verify", json={"token": token})

    assert response.status_code == 200
    assert response.json()["status"] == "verified"

    session.refresh(user)
    assert user.email_verified_at is not None


def test_login_success_sets_cookie_and_creates_session(client, session, create_user):
    user = create_user("login_ok@example.com")

    response = client.post(
        "/api/auth/login",
        json={"email": "login_ok@example.com", "password": DEFAULT_PASSWORD},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "logged_in"
    assert "session_token" in response.cookies

    token_hash = hash_session_token(response.cookies["session_token"])
    stored_session = session.scalar(select(Session).where(Session.token_hash == token_hash))
    assert stored_session is not None
    assert stored_session.user_id == user.id
    assert stored_session.revoked_at is None


def test_login_requires_verified_email(client, create_user, require_email_verification):
    create_user("login_unverified@example.com", verified=False)

    response = client.post(
        "/api/auth/login",
        json={"email": "login_unverified@example.com", "password": DEFAULT_PASSWORD},
    )

    assert response.status_code == 403


def test_logout_revokes_session_and_clears_cookie(client, session, create_user, login):
    create_user("logout_ok@example.com")

    login_response = login("logout_ok@example.com")
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


def test_delete_account_success_anonymizes_and_revokes_sessions(client, session, logged_in_user):
    user = logged_in_user("delete_ok@example.com")
    original_email_hash = user.email_hash

    response = client.post(
        "/api/auth/delete-account",
        json={"current_password": DEFAULT_PASSWORD},
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
        json={"current_password": DEFAULT_PASSWORD},
    )

    assert response.status_code == 401


def test_delete_account_requires_correct_password(client, session, logged_in_user):
    user = logged_in_user("delete_wrong_pass@example.com")

    response = client.post(
        "/api/auth/delete-account",
        json={"current_password": "contrasenya_incorrecta"},
    )

    assert response.status_code == 401

    session.refresh(user)
    assert user.deleted_at is None
    assert user.email == "delete_wrong_pass@example.com"
    assert user.password_hash is not None


def test_export_data_returns_user_and_votes(client, session, logged_in_user):
    user = logged_in_user("export_ok@example.com")

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


def test_get_ranking_unkwnown_category(client):
    """Prova què passa quan intentem obtenir el rànquing d'una categoria no existent."""
    category_code = "cat_inexistent"
    response = client.get(f"/api/ranking?category_code={category_code}")
    assert response.status_code == 404
    assert response.json()["detail"] == f"No existeix la categoria: {category_code}."


def test_get_ranking_empty_category(client, session):
    """Prova què passa quan intentem obtenir el rànquing d'una categoria buida."""
    # Creem una categoria sense vots
    c = Category(code="test_cat", name="Categoria de prova")
    session.add(c)
    session.commit()

    response = client.get(f"/api/ranking?category_code={c.code}")
    assert response.json()["best_model"] is None
    assert response.json()["bt_skills"] == {}


def test_get_ranking_full_category(client, session):
    """Prova què passa quan intentem obtenir el rànquing d'una categoria amb vots."""
    # Recuperem la categoria 'correccio'
    c = session.scalar(select(Category).where(Category.code == "correccio"))

    # Inserim dades falses
    p = Prompt(version="v1", code="correccio", category_id=c.id, text="El gat es blau")
    session.add(p)
    session.commit()

    r1 = Response(prompt_id=p.id, model="model_1", text="El gat és blau")
    r2 = Response(prompt_id=p.id, model="model_2", text="El gat es color blau")
    session.add_all([r1, r2])
    session.commit()

    v1 = Vote(prompt_id=p.id, response_a_id=r1.id, response_b_id=r2.id, winner="a")
    session.add(v1)
    session.commit()

    # Obtenim resposta
    response = client.get(f"/api/ranking?category_code={c.code}")
    assert response.status_code == 200
    assert response.json()["best_model"] == "model_1"
    assert response.json()["bt_skills"] != {}
