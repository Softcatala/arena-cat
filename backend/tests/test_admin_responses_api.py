"""Gestió d'inferències des de l'administració i el seu efecte en tasques i rànquing."""

import pytest
from sqlalchemy import select

from app.models import Category, Prompt, Response, TaskSkip, Vote, Winner


@pytest.fixture
def prompt(session) -> Prompt:
    category = session.scalar(select(Category).where(Category.code == "correccio"))
    prompt = Prompt(version="v1", code="correccio_80", category_id=category.id, text="Text base")
    session.add(prompt)
    session.commit()
    return prompt


def add_response(session, prompt, model, text="Resposta") -> Response:
    response = Response(prompt_id=prompt.id, model=model, text=text)
    session.add(response)
    session.commit()
    return response


def vote(session, prompt, response_a, response_b, winner=Winner.a, user_id=None) -> Vote:
    row = Vote(
        prompt_id=prompt.id,
        user_id=user_id,
        response_a_id=response_a.id,
        response_b_id=response_b.id,
        winner=winner,
    )
    session.add(row)
    session.commit()
    return row


def test_response_endpoints_require_a_session(client):
    assert client.get("/api/admin/responses").status_code == 401
    assert client.post("/api/admin/responses", json={}).status_code == 401
    assert client.patch("/api/admin/responses/1", json={"active": False}).status_code == 401
    assert client.delete("/api/admin/responses/1").status_code == 401


def test_response_endpoints_require_an_admin(client, logged_in_user):
    logged_in_user("regular@example.com")
    assert client.get("/api/admin/responses").status_code == 403
    assert client.post("/api/admin/responses", json={}).status_code == 403
    assert client.patch("/api/admin/responses/1", json={"active": False}).status_code == 403
    assert client.delete("/api/admin/responses/1").status_code == 403


def test_create_response_is_active_and_counts_in_the_ranking(client, admin, session, prompt):
    result = client.post(
        "/api/admin/responses",
        json={
            "prompt_id": prompt.id,
            "model": "model-a",
            "text": "  Una resposta.  ",
            "inference_metadata": {"temperature": 0.7},
        },
    )

    assert result.status_code == 201
    body = result.json()
    assert body["active"] is True
    assert body["included_in_ranking"] is True
    assert body["text"] == "Una resposta."
    assert body["vote_count"] == 0
    stored = session.get(Response, body["id"])
    assert stored.inference_metadata == {"temperature": 0.7}


def test_create_response_for_an_unknown_prompt(client, admin):
    result = client.post(
        "/api/admin/responses", json={"prompt_id": 999999, "model": "model-a", "text": "x"}
    )

    assert result.status_code == 404


def test_create_rejects_a_second_response_of_the_same_model(client, admin, session, prompt):
    add_response(session, prompt, "model-a")

    result = client.post(
        "/api/admin/responses",
        json={"prompt_id": prompt.id, "model": "model-a", "text": "Una altra"},
    )

    assert result.status_code == 409


@pytest.mark.parametrize("overrides", [{"model": ""}, {"text": "   "}, {"text": ""}])
def test_create_validates_the_fields(client, admin, prompt, overrides):
    body = {"prompt_id": prompt.id, "model": "model-a", "text": "Resposta", **overrides}

    assert client.post("/api/admin/responses", json=body).status_code == 422


def test_list_responses_with_vote_counts_and_filters(client, admin, session, prompt):
    first = add_response(session, prompt, "model-a")
    second = add_response(session, prompt, "model-b")
    third = add_response(session, prompt, "model-c")
    vote(session, prompt, first, second)
    vote(session, prompt, third, first)
    second.active = False
    session.commit()

    everything = client.get("/api/admin/responses").json()
    inactive = client.get("/api/admin/responses", params={"active": "false"}).json()
    by_model = client.get("/api/admin/responses", params={"model": "model-a"}).json()
    by_prompt = client.get("/api/admin/responses", params={"prompt_id": prompt.id}).json()

    counts = {item["model"]: item["vote_count"] for item in everything["responses"]}
    assert counts == {"model-a": 2, "model-b": 1, "model-c": 1}
    assert everything["total"] == 3
    assert [item["model"] for item in inactive["responses"]] == ["model-b"]
    assert [item["model"] for item in by_model["responses"]] == ["model-a"]
    assert by_prompt["total"] == 3


def test_patch_changes_the_flags(client, admin, session, prompt):
    response = add_response(session, prompt, "model-a")

    result = client.patch(
        f"/api/admin/responses/{response.id}",
        json={"active": False, "included_in_ranking": False},
    )

    assert result.status_code == 200
    assert result.json()["active"] is False
    assert result.json()["included_in_ranking"] is False
    session.refresh(response)
    assert (response.active, response.included_in_ranking) == (False, False)


def test_patch_changes_only_the_given_flag(client, admin, session, prompt):
    response = add_response(session, prompt, "model-a")

    client.patch(f"/api/admin/responses/{response.id}", json={"active": False})

    session.refresh(response)
    assert (response.active, response.included_in_ranking) == (False, True)


def test_patch_requires_at_least_one_field(client, admin, session, prompt):
    response = add_response(session, prompt, "model-a")

    assert client.patch(f"/api/admin/responses/{response.id}", json={}).status_code == 422


def test_patch_unknown_response(client, admin):
    assert client.patch("/api/admin/responses/999999", json={"active": False}).status_code == 404


def test_delete_response_without_votes(client, admin, session, prompt):
    response = add_response(session, prompt, "model-a")

    result = client.delete(f"/api/admin/responses/{response.id}")

    assert result.status_code == 204
    assert session.get(Response, response.id) is None


def test_delete_response_with_votes_is_refused(client, admin, session, prompt):
    first = add_response(session, prompt, "model-a")
    second = add_response(session, prompt, "model-b")
    vote(session, prompt, first, second)

    result = client.delete(f"/api/admin/responses/{second.id}")

    assert result.status_code == 409
    assert session.get(Response, second.id) is not None


def test_delete_response_with_skips_is_refused(client, admin, session, prompt):
    first = add_response(session, prompt, "model-a")
    second = add_response(session, prompt, "model-b")
    session.add(
        TaskSkip(
            prompt_id=prompt.id,
            user_id=admin.id,
            response_a_id=first.id,
            response_b_id=second.id,
        )
    )
    session.commit()

    assert client.delete(f"/api/admin/responses/{first.id}").status_code == 409


def test_delete_unknown_response(client, admin):
    assert client.delete("/api/admin/responses/999999").status_code == 404


# ---------------------------------------------------------------------------
# Efecte en les tasques, el progrés i el rànquing.
# ---------------------------------------------------------------------------


def test_inactive_response_is_not_served(client, admin, session, prompt):
    add_response(session, prompt, "model-a", "Resposta de A")
    add_response(session, prompt, "model-b", "Resposta de B")
    third = add_response(session, prompt, "model-c", "Resposta de C")
    third.active = False
    session.commit()

    for _ in range(10):
        task = client.get("/api/task").json()
        assert "Resposta de C" not in (task["response_a"], task["response_b"])


def test_prompt_with_fewer_than_two_active_responses_is_not_served(client, admin, session, prompt):
    add_response(session, prompt, "model-a")
    second = add_response(session, prompt, "model-b")
    second.active = False
    session.commit()

    assert client.get("/api/task").status_code == 404


def test_progress_ignores_inactive_responses(client, admin, session, prompt):
    add_response(session, prompt, "model-a")
    add_response(session, prompt, "model-b")
    third = add_response(session, prompt, "model-c")

    assert client.get("/api/task/progress").json()["total"] == 3

    third.active = False
    session.commit()

    assert client.get("/api/task/progress").json()["total"] == 1


def test_votes_on_excluded_responses_do_not_count_in_the_ranking(client, session, prompt):
    first = add_response(session, prompt, "model-a")
    second = add_response(session, prompt, "model-b")
    third = add_response(session, prompt, "model-c")
    vote(session, prompt, first, second)
    vote(session, prompt, first, third)

    assert client.get("/api/ranking").json()["n_votes_total"] == 2

    third.included_in_ranking = False
    session.commit()

    assert client.get("/api/ranking").json()["n_votes_total"] == 1


def test_ranking_cache_follows_the_inclusion_flag(client, admin, session, prompt):
    first = add_response(session, prompt, "model-a")
    second = add_response(session, prompt, "model-b")
    vote(session, prompt, first, second)
    assert client.get("/api/ranking").json()["n_votes_total"] == 1

    client.patch(f"/api/admin/responses/{second.id}", json={"included_in_ranking": False})

    assert client.get("/api/ranking").json()["n_votes_total"] == 0

    client.patch(f"/api/admin/responses/{second.id}", json={"included_in_ranking": True})

    assert client.get("/api/ranking").json()["n_votes_total"] == 1
