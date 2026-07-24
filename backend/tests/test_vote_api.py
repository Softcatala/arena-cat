from app.models import Prompt, Response
from app.security import create_task_token


def test_post_vote_invalid_token(client, logged_in_user):
    """Prova d'enviar un vot amb un token inventat."""
    logged_in_user("vote_invalid@example.com")
    response = client.post("/api/vote", json={"winner": "a", "token": "inventat"})
    assert response.status_code == 401


def test_post_vote_requires_auth(client):
    response = client.post("/api/vote", json={"winner": "a", "token": "inventat"})
    assert response.status_code == 401


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

    token = create_task_token(p.id, r1.id, r2.id, user_id=user.id)

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
    token = create_task_token(p.id, r1.id, r2.id, user_id=user.id)

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
    owner_token = create_task_token(p.id, r1.id, r2.id, user_id=owner_user.id)
    client.post("/api/auth/logout")

    logged_in_user("other_vote@example.com")
    response = client.post("/api/vote", json={"winner": "a", "token": owner_token})

    assert response.status_code == 403
