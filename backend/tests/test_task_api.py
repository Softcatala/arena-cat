from app.models import Category, Prompt, Response


def test_get_task_empty_db(client, logged_in_user):
    """Prova què passa si demanem una tasca quan la db està buida."""
    logged_in_user("task_empty@example.com")

    response = client.get("/api/task", params={"category_code": "correccio"})

    assert response.status_code == 404
    assert response.json()["detail"] == "No hi ha tasques disponibles o bé les has realitzat totes."


def test_get_task_with_data(client, session, logged_in_user):
    """Prova què passa quan hi ha dades a la db."""
    c = Category(code="test_cat", name="Categoria de prova")
    session.add(c)
    session.commit()

    p = Prompt(version="v1", code="test_p", category_id=c.id, text="El gat es blau")
    session.add(p)
    session.commit()

    r1 = Response(prompt_id=p.id, model="model_1", text="El gat és blau")
    r2 = Response(prompt_id=p.id, model="model_2", text="El gat es color blau")
    session.add_all([r1, r2])
    session.commit()

    logged_in_user("task_data@example.com")

    response = client.get("/api/task", params={"category_code": "test_cat"})
    assert response.status_code == 200
    data = response.json()
    assert data["prompt"] == "El gat es blau"
    assert "token" in data


def test_get_task_requires_auth(client):
    response = client.get("/api/task", params={"category_code": "correccio"})
    assert response.status_code == 401
