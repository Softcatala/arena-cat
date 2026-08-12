from datetime import UTC, datetime, timedelta

from app.models import Prompt, Response
from app.security import create_task_token


def ready_task_token(prompt_id, response_a_id, response_b_id, user_id):
    return create_task_token(
        prompt_id,
        response_a_id,
        response_b_id,
        user_id=user_id,
        vote_after=datetime.now(UTC) - timedelta(seconds=1),
    )


def test_post_vote_invalid_token(client, logged_in_user):
    """Prova d'enviar un vot amb un token inventat.

    El 401 porta `error_code: task_token_invalid` perquè el frontend el pugui
    distingir d'un 401 de sessió caducada (la sessió hi segueix sent vàlida).
    """
    logged_in_user("vote_invalid@example.com")
    response = client.post("/api/vote", json={"winner": "a", "token": "inventat"})
    assert response.status_code == 401
    assert response.json()["error_code"] == "task_token_invalid"


def test_post_vote_requires_auth(client):
    """Sense sessió el 401 és de sessió, no de token: no porta `error_code`."""
    response = client.post("/api/vote", json={"winner": "a", "token": "inventat"})
    assert response.status_code == 401
    assert "error_code" not in response.json()


def test_post_vote_success(client, session, logged_in_user):
    """Prova què passa quan enviem un vot vàlid i sencer."""
    p = Prompt(version="v1", code="test_p2", category_id=1, text="Bon dia")
    session.add(p)
    session.commit()
    r1 = Response(prompt_id=p.id, model="model_A", text="Hola")
    r2 = Response(prompt_id=p.id, model="model_B", text="Bon dia")
    session.add_all([r1, r2])
    session.commit()

    user = logged_in_user("vote_ok@example.com")

    token = ready_task_token(p.id, r1.id, r2.id, user.id)

    response = client.post("/api/vote", json={"winner": "a", "token": token})
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_post_vote_rejects_duplicate_token(client, session, logged_in_user):
    """Reenviar el mateix token vàlid no ha de crear un segon vot."""
    p = Prompt(version="v1", code="test_dup", category_id=1, text="Bon dia")
    session.add(p)
    session.commit()
    r1 = Response(prompt_id=p.id, model="model_A", text="Hola")
    r2 = Response(prompt_id=p.id, model="model_B", text="Bon dia")
    session.add_all([r1, r2])
    session.commit()

    user = logged_in_user("vote_dup@example.com")
    token = ready_task_token(p.id, r1.id, r2.id, user.id)

    first = client.post("/api/vote", json={"winner": "a", "token": token})
    assert first.status_code == 200

    second = client.post("/api/vote", json={"winner": "b", "token": token})
    assert second.status_code == 409


def test_post_vote_rejects_token_from_other_user(client, session, logged_in_user):
    p = Prompt(version="v1", code="test_p3", category_id=1, text="Hola món")
    session.add(p)
    session.commit()
    r1 = Response(prompt_id=p.id, model="model_A", text="A")
    r2 = Response(prompt_id=p.id, model="model_B", text="B")
    session.add_all([r1, r2])
    session.commit()

    owner_user = logged_in_user("owner_vote@example.com")
    owner_token = ready_task_token(p.id, r1.id, r2.id, owner_user.id)
    client.post("/api/auth/logout")

    logged_in_user("other_vote@example.com")
    response = client.post("/api/vote", json={"winner": "a", "token": owner_token})

    assert response.status_code == 403


def test_post_vote_rejects_vote_before_reading_time(client, session, logged_in_user):
    p = Prompt(version="v1", code="test_too_fast", category_id=1, text="Hola món")
    session.add(p)
    session.commit()
    r1 = Response(prompt_id=p.id, model="model_A", text="A")
    r2 = Response(prompt_id=p.id, model="model_B", text="B")
    session.add_all([r1, r2])
    session.commit()

    user = logged_in_user("vote_too_fast@example.com")
    token = create_task_token(p.id, r1.id, r2.id, user_id=user.id)

    response = client.post("/api/vote", json={"winner": "a", "token": token})

    assert response.status_code == 425
