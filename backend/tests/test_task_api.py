import random

import pytest

from app.models import Category, Prompt, Response, TaskSkip, Vote, Winner


@pytest.mark.parametrize("params", [{}, {"category_code": "correccio"}])
def test_get_task_empty_db(client, logged_in_user, params):
    """Prova què passa si demanem una tasca quan la db està buida."""
    logged_in_user("task_empty@example.com")

    response = client.get("/api/task", params=params)

    assert response.status_code == 404
    assert response.json()["detail"] == "No hi ha tasques disponibles o bé les heu realitzat totes."


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


@pytest.fixture
def category_tasks(session):
    tasks = {}
    for code in ("a_category", "z_category"):
        category = Category(code=code, name=code)
        session.add(category)
        session.flush()
        prompt = Prompt(version="v1", code=code, category_id=category.id, text="Text")
        session.add(prompt)
        session.flush()
        responses = [Response(prompt_id=prompt.id, model=model, text=model) for model in ("a", "b")]
        session.add_all(responses)
        session.flush()
        tasks[code] = (prompt, *responses)
    session.commit()
    return tasks


def test_unfiltered_tasks_can_select_each_available_category(
    client, logged_in_user, category_tasks, monkeypatch
):
    """Les peticions sense filtre no es concentren en la primera categoria."""
    monkeypatch.setattr(random, "shuffle", random.Random(0).shuffle)
    logged_in_user("random_category@example.com")
    selected = set()
    for _ in range(12):
        response = client.get("/api/task")
        assert response.status_code == 200
        selected.add(response.json()["category_code"])
    assert selected == set(category_tasks)


@pytest.mark.parametrize("completed", [Vote, TaskSkip])
def test_unfiltered_tasks_exclude_categories_completed_by_user(
    client, session, logged_in_user, category_tasks, completed
):
    """Les categories votades o omeses no impedeixen accedir a les altres."""
    user = logged_in_user("completed_category@example.com")
    for code, (prompt, response_a, response_b) in category_tasks.items():
        session.add(
            completed(
                prompt_id=prompt.id,
                user_id=user.id,
                response_a_id=response_a.id,
                response_b_id=response_b.id,
                **({"winner": Winner.a} if completed is Vote else {}),
            )
        )
        session.commit()
        response = client.get("/api/task")
        if code == "a_category":
            assert response.status_code == 200
            assert response.json()["category_code"] == "z_category"
        else:
            assert response.status_code == 404


def test_filtered_tasks_keep_requested_category(client, logged_in_user, category_tasks):
    """El filtre explícit continua seleccionant només la categoria demanada."""
    logged_in_user("filtered_category@example.com")
    for code in category_tasks:
        response = client.get("/api/task", params={"category_code": code})
        assert response.status_code == 200
        assert response.json()["category_code"] == code


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
