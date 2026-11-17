"""CORS restringit i protecció contra peticions d'escriptura des d'un origen no autoritzat."""

import pytest

from app.models import User

ALLOWED = "https://arena.example.org"
UNTRUSTED = "https://untrusted.example.org"


def test_allowed_origin_can_read_responses_with_credentials(client, admin):
    result = client.get("/api/admin/users", headers={"Origin": ALLOWED})

    assert result.status_code == 200
    assert result.headers["access-control-allow-origin"] == ALLOWED
    assert result.headers["access-control-allow-credentials"] == "true"


def test_untrusted_origin_cannot_read_responses(client, admin):
    """Sense `Access-Control-Allow-Origin` el navegador no entrega la resposta a la pàgina."""
    result = client.get("/api/admin/users", headers={"Origin": UNTRUSTED})

    assert "access-control-allow-origin" not in result.headers


def test_preflight_from_an_untrusted_origin_is_refused(client):
    result = client.options(
        "/api/admin/users/1/block",
        headers={"Origin": UNTRUSTED, "Access-Control-Request-Method": "POST"},
    )

    assert result.status_code == 400
    assert "access-control-allow-origin" not in result.headers


def test_preflight_from_an_allowed_origin_is_accepted(client):
    result = client.options(
        "/api/admin/users/1/block",
        headers={
            "Origin": ALLOWED,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert result.status_code == 200
    assert result.headers["access-control-allow-origin"] == ALLOWED


def test_untrusted_origin_cannot_block_a_user(client, admin, create_user, session):
    target = create_user("target@example.com")

    result = client.post(f"/api/admin/users/{target.id}/block", headers={"Origin": UNTRUSTED})

    assert result.status_code == 403
    session.refresh(target)
    assert target.blocked_at is None


@pytest.mark.parametrize("origin", [UNTRUSTED, "null", "http://arena.example.org"])
@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_writes_from_other_origins_are_refused(client, admin, method, origin):
    result = client.request(method, "/api/admin/prompts/1", headers={"Origin": origin})

    assert result.status_code == 403


def test_untrusted_origin_cannot_log_in(client, create_user):
    create_user("someone@example.com")

    result = client.post(
        "/api/auth/login",
        json={"email": "someone@example.com", "password": "ContrasenyaSegura123!"},
        headers={"Origin": UNTRUSTED},
    )

    assert result.status_code == 403
    assert "set-cookie" not in result.headers


def test_allowed_origin_can_block_a_user(client, admin, create_user, session):
    target = create_user("target@example.com")

    result = client.post(f"/api/admin/users/{target.id}/block", headers={"Origin": ALLOWED})

    assert result.status_code == 200
    session.refresh(target)
    assert isinstance(target, User) and target.blocked_at is not None


def test_same_origin_writes_are_accepted_without_configuration(client, admin, create_user):
    """Un navegador que parla amb l'API a través del proxy del frontend envia el mateix origen."""
    target = create_user("target@example.com")

    result = client.post(
        f"/api/admin/users/{target.id}/block", headers={"Origin": "https://testserver"}
    )

    assert result.status_code == 200


def test_writes_without_an_origin_header_are_accepted(client, admin, create_user):
    """Els clients que no són navegadors (curl, scripts) no envien `Origin`."""
    target = create_user("target@example.com")

    assert client.post(f"/api/admin/users/{target.id}/block").status_code == 200


def test_reads_from_untrusted_origins_are_not_blocked_by_the_origin_check(client):
    """La lectura es protegeix amb CORS: el navegador no en deixa veure la resposta."""
    assert client.get("/api/categories", headers={"Origin": UNTRUSTED}).status_code == 200
