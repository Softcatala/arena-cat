import pytest
from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app
from app.models import Prompt, Response


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
    response = client.get("/api/task")

    # Comprovem el status code
    assert response.status_code == 404

    # Comprovem el missatge
    assert response.json()["detail"] == "No hi ha prompts disponibles"


def test_get_task_with_data(client, session):
    """Prova què passa quan hi ha dades a la db."""
    # Inserim dades falses
    p = Prompt(version="v1", code="test_p", category_id=1, text="El gat es blau")
    session.add(p)
    session.commit()

    r1 = Response(prompt_id=p.id, model="model_1", text="El gat és blau")
    r2 = Response(prompt_id=p.id, model="model_2", text="El gat es color blau")
    session.add_all([r1, r2])
    session.commit()

    # Fem la petició GET a la API
    response = client.get("/api/task")
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

    from app.security import create_token
    token = create_token(p.id, r1.id, r2.id)

    # Enviem el vot amb el token
    response = client.post("/api/vote", json={"winner": "a", "token": token})
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
