from app.models import Category, Prompt, Response, TaskSkip, Vote, Winner


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
    assert data["category_code"] == "test_cat"
    assert data["prompt"] == "El gat es blau"
    assert "token" in data


def test_get_task_without_category_picks_available_task(client, session, logged_in_user):
    """Si no s'indica categoria, retorna una tasca disponible de qualsevol categoria."""
    c = Category(code="available_cat", name="Categoria disponible")
    session.add(c)
    session.commit()

    p = Prompt(version="v1", code="available_p", category_id=c.id, text="El gat es blau")
    session.add(p)
    session.commit()

    r1 = Response(prompt_id=p.id, model="model_1", text="El gat és blau")
    r2 = Response(prompt_id=p.id, model="model_2", text="El gat es color blau")
    session.add_all([r1, r2])
    session.commit()

    logged_in_user("task_any_category@example.com")

    response = client.get("/api/task")

    assert response.status_code == 200
    data = response.json()
    assert data["category_code"] == "available_cat"
    assert data["prompt"] == "El gat es blau"
    assert "token" in data


def test_skip_task_prevents_showing_it_again(client, session, logged_in_user):
    """Ometre una tasca fa que no es torni a oferir al mateix usuari."""
    c = Category(code="skip_cat", name="Categoria omissió")
    session.add(c)
    session.commit()

    p = Prompt(version="v1", code="skip_p", category_id=c.id, text="El gat es blau")
    session.add(p)
    session.commit()

    r1 = Response(prompt_id=p.id, model="model_1", text="El gat és blau")
    r2 = Response(prompt_id=p.id, model="model_2", text="El gat es color blau")
    session.add_all([r1, r2])
    session.commit()

    logged_in_user("task_skip@example.com")

    task = client.get("/api/task", params={"category_code": "skip_cat"})
    assert task.status_code == 200

    skip = client.post("/api/task/skip", json={"token": task.json()["token"]})
    assert skip.status_code == 200
    assert skip.json()["status"] == "ok"

    next_task = client.get("/api/task", params={"category_code": "skip_cat"})
    assert next_task.status_code == 404


def test_task_progress_counts_voted_skipped_and_remaining(client, session, logged_in_user):
    """El progrés compta totes les parelles globals i l'estat de l'usuari."""
    c = Category(code="progress_cat", name="Categoria progrés")
    session.add(c)
    session.commit()

    p = Prompt(version="v1", code="progress_p", category_id=c.id, text="El gat es blau")
    session.add(p)
    session.commit()

    r1 = Response(prompt_id=p.id, model="model_1", text="Resposta 1")
    r2 = Response(prompt_id=p.id, model="model_2", text="Resposta 2")
    r3 = Response(prompt_id=p.id, model="model_3", text="Resposta 3")
    session.add_all([r1, r2, r3])
    session.commit()

    user = logged_in_user("task_progress@example.com")
    session.add(
        Vote(
            prompt_id=p.id,
            user_id=user.id,
            response_a_id=r1.id,
            response_b_id=r2.id,
            winner=Winner.a,
        )
    )
    session.add(
        TaskSkip(
            prompt_id=p.id,
            user_id=user.id,
            response_a_id=r1.id,
            response_b_id=r3.id,
        )
    )
    session.commit()

    response = client.get("/api/task/progress")

    assert response.status_code == 200
    assert response.json() == {
        "total": 3,
        "voted": 1,
        "skipped": 1,
        "remaining": 1,
    }


def test_get_task_requires_auth(client):
    response = client.get("/api/task", params={"category_code": "correccio"})
    assert response.status_code == 401


def test_skip_task_invalid_token(client, logged_in_user):
    """El 401 d'un token de tasca invàlid porta `error_code: task_token_invalid`,
    igual que a `/vote`, perquè el frontend no el confongui amb sessió caducada.
    """
    logged_in_user("task_skip_invalid@example.com")
    response = client.post("/api/task/skip", json={"token": "inventat"})
    assert response.status_code == 401
    assert response.json()["error_code"] == "task_token_invalid"
