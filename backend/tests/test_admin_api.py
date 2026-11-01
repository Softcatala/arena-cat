"""Accés d'administració: rol d'administrador, llistat d'usuaris i bloqueig."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.main import app
from app.models import Session, User


def test_admin_endpoints_require_a_session(client):
    assert client.get("/api/admin/users").status_code == 401
    assert client.post("/api/admin/users/1/block").status_code == 401


def test_regular_user_is_forbidden(client, logged_in_user):
    logged_in_user("regular@example.com")
    assert client.get("/api/admin/users").status_code == 403
    assert client.post("/api/admin/users/1/block").status_code == 403


def test_admin_must_have_a_verified_email(client, create_user, login, session, monkeypatch):
    monkeypatch.setenv("REQUIRE_EMAIL_VERIFICATION", "false")
    from app.config import get_settings

    get_settings.cache_clear()
    user = create_user("unverified@example.com", verified=False)
    user.is_admin = True
    session.commit()
    login("unverified@example.com")

    monkeypatch.setenv("REQUIRE_EMAIL_VERIFICATION", "true")
    get_settings.cache_clear()
    assert client.get("/api/admin/users").status_code == 403


def test_admin_lists_users(client, admin, create_user):
    create_user("other@example.com", qualified=False)

    result = client.get("/api/admin/users")

    assert result.status_code == 200
    users = {user["email"]: user for user in result.json()["users"]}
    assert users["admin@example.com"]["is_admin"] is True
    assert users["other@example.com"]["is_admin"] is False
    assert users["other@example.com"]["qualified_at"] is None
    assert users["other@example.com"]["blocked_at"] is None
    assert "password_hash" not in users["other@example.com"]


def test_admin_list_is_paginated_and_ordered_by_id(client, admin, create_user):
    for index in range(3):
        create_user(f"user{index}@example.com")

    first = client.get("/api/admin/users", params={"limit": 2}).json()
    second = client.get("/api/admin/users", params={"limit": 2, "offset": 2}).json()

    ids = [user["id"] for user in first["users"] + second["users"]]
    assert len(first["users"]) == 2
    assert ids == sorted(ids)
    assert first["total"] == 4


def test_block_rejects_login_and_revokes_sessions(client, admin, create_user, session):
    target = create_user("target@example.com")

    other = TestClient(app, base_url="https://testserver")
    other.post(
        "/api/auth/login",
        json={"email": "target@example.com", "password": "ContrasenyaSegura123!"},
    )
    assert other.get("/api/auth/session").json()["authenticated"] is True

    result = client.post(f"/api/admin/users/{target.id}/block")

    assert result.status_code == 200
    assert result.json()["blocked_at"] is not None
    assert other.get("/api/auth/session").json()["authenticated"] is False
    active = session.scalars(
        select(Session).where(Session.user_id == target.id, Session.revoked_at.is_(None))
    ).all()
    assert active == []
    denied = other.post(
        "/api/auth/login",
        json={"email": "target@example.com", "password": "ContrasenyaSegura123!"},
    )
    assert denied.status_code == 403


def test_blocked_user_with_wrong_password_gets_the_generic_error(client, admin, create_user):
    target = create_user("target@example.com")
    client.post(f"/api/admin/users/{target.id}/block")

    denied = client.post(
        "/api/auth/login", json={"email": "target@example.com", "password": "incorrecta"}
    )

    assert denied.status_code == 401


def test_block_is_idempotent_and_keeps_the_first_date(client, admin, create_user):
    target = create_user("target@example.com")

    first = client.post(f"/api/admin/users/{target.id}/block").json()
    second = client.post(f"/api/admin/users/{target.id}/block").json()

    assert first["blocked_at"] == second["blocked_at"]


def test_unblock_allows_login_again(client, admin, create_user):
    target = create_user("target@example.com")
    client.post(f"/api/admin/users/{target.id}/block")

    result = client.post(f"/api/admin/users/{target.id}/unblock")

    assert result.status_code == 200
    assert result.json()["blocked_at"] is None
    allowed = client.post(
        "/api/auth/login",
        json={"email": "target@example.com", "password": "ContrasenyaSegura123!"},
    )
    assert allowed.status_code == 200


def test_admin_cannot_block_themselves(client, admin):
    result = client.post(f"/api/admin/users/{admin.id}/block")

    assert result.status_code == 409
    assert client.get("/api/admin/users").status_code == 200


def test_block_unknown_user_is_not_found(client, admin):
    assert client.post("/api/admin/users/999999/block").status_code == 404
    assert client.post("/api/admin/users/999999/unblock").status_code == 404


def test_deleted_account_cannot_be_blocked(client, admin, create_user, session):
    target = create_user("gone@example.com")
    target.deleted_at = datetime.now(UTC)
    target.email = target.email_hash = target.password_hash = target.consent_at = None
    session.commit()

    assert client.post(f"/api/admin/users/{target.id}/block").status_code == 409


def test_account_deletion_removes_the_admin_role(client, admin, session):
    result = client.post(
        "/api/auth/delete-account", json={"current_password": "ContrasenyaSegura123!"}
    )

    assert result.status_code == 200
    session.refresh(admin)
    assert admin.is_admin is False


def test_database_rejects_deleted_admins(create_user, session):
    user = create_user("former@example.com")
    user.is_admin = True
    user.deleted_at = datetime.now(UTC)
    user.email = user.email_hash = user.password_hash = user.consent_at = None

    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_new_users_are_not_admins(create_user):
    user = create_user("new@example.com")

    assert user.is_admin is False
    assert user.blocked_at is None
    assert isinstance(user, User)


def test_session_exposes_the_admin_role(client, admin, create_user, login):
    assert client.get("/api/auth/session").json()["is_admin"] is True

    other = TestClient(app, base_url="https://testserver")
    create_user("plain@example.com")
    other.post(
        "/api/auth/login",
        json={"email": "plain@example.com", "password": "ContrasenyaSegura123!"},
    )
    assert other.get("/api/auth/session").json()["is_admin"] is False


def test_anonymous_session_is_not_admin(client):
    assert client.get("/api/auth/session").json()["is_admin"] is False
