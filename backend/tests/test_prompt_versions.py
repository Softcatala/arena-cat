"""Les revisions actives substitueixen cada prompt sense perdre'n l'historial."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.models import Category, Prompt, Response, TaskSkip, Vote, Winner
from app.ranking.sampler import _load_prompts_and_responses
from app.security import create_task_token


@pytest.fixture
def make_prompt(session):
    category_id = session.scalar(select(Category.id).where(Category.code == "correccio"))

    def create(code, version, n_responses=2):
        prompt = Prompt(code=code, version=version, category_id=category_id, text=version)
        session.add(prompt)
        session.flush()
        responses = [
            Response(prompt_id=prompt.id, model=f"model-{i}", text=f"Resposta {i}")
            for i in range(n_responses)
        ]
        session.add_all(responses)
        session.commit()
        return prompt, responses

    return create


def test_activation_updates_tasks_progress_ranking_and_preserves_history(
    client, session, logged_in_user, create_user, make_prompt
):
    user = logged_in_user("versions@example.com")
    other = create_user("versions-other@example.com")
    old, responses = make_prompt("correccio_1", "v1", 3)
    unchanged, other_responses = make_prompt("correccio_2", "v1")
    session.add_all(
        [
            Vote(
                prompt_id=old.id,
                user_id=user.id,
                response_a_id=responses[0].id,
                response_b_id=responses[1].id,
                winner=Winner.a,
            ),
            TaskSkip(
                prompt_id=old.id,
                user_id=user.id,
                response_a_id=responses[0].id,
                response_b_id=responses[2].id,
            ),
            Vote(
                prompt_id=unchanged.id,
                user_id=other.id,
                response_a_id=other_responses[0].id,
                response_b_id=other_responses[1].id,
                winner=Winner.b,
            ),
        ]
    )
    session.commit()
    new, new_responses = make_prompt("correccio_1", "v2", 1)

    def active_ids():
        return {p.id for p, _ in _load_prompts_and_responses(session, "correccio")}

    assert active_ids() == {old.id, unchanged.id}
    assert client.get("/api/task/progress").json() == {
        "total": 4,
        "voted": 1,
        "skipped": 1,
        "remaining": 2,
    }
    assert client.get("/api/ranking").json()["n_votes_total"] == 2

    second = Response(prompt_id=new.id, model="model-1", text="Resposta nova")
    session.add(second)
    session.commit()
    assert active_ids() == {new.id, unchanged.id}
    assert client.get("/api/task/progress").json() == {
        "total": 2,
        "voted": 0,
        "skipped": 0,
        "remaining": 2,
    }
    for params in ({}, {"category_code": "correccio"}):
        ranking = client.get("/api/ranking", params=params).json()
        assert ranking["n_votes_total"] == ranking["n_participants"] == 1
        assert ranking["best_model"] == "model-1"
        assert ranking["confidence"]["n_decisive_votes"] == 1
        assert ranking["confidence"]["n_prompts"] == 1

    token = create_task_token(
        new.id,
        new_responses[0].id,
        second.id,
        user.id,
        vote_after=datetime.now(UTC) - timedelta(seconds=1),
    )
    assert client.post("/api/vote", json={"token": token, "winner": "b"}).status_code == 200
    assert client.get("/api/task").json()["prompt"] == unchanged.text
    assert client.get("/api/task/progress").json()["voted"] == 1
    assert client.get("/api/ranking").json()["n_participants"] == 2
    assert len(client.get("/api/auth/export").json()["votes"]) == 2
    assert session.scalar(select(func.count()).select_from(Vote)) == 3
    assert session.scalar(select(func.count()).select_from(TaskSkip)) == 1


def test_versions_are_ordered_numerically_not_by_insertion(session, make_prompt):
    latest, _ = make_prompt("correccio_1", "v10")
    make_prompt("correccio_1", "v2")
    make_prompt("correccio_1", "v9")
    make_prompt("correccio_1", "v11", 1)
    assert [p.id for p, _ in _load_prompts_and_responses(session, "correccio")] == [latest.id]


def test_mock_data_uses_valid_versions_and_cleanup_preserves_real_prompts(session, make_prompt):
    from scripts.seed_mock_tasks import DEFAULT_VERSION, clear_mock_tasks, seed_mock_tasks

    real, _ = make_prompt("correccio_1", "v1")
    seed_mock_tasks(
        session,
        version=DEFAULT_VERSION,
        prompts_per_category=1,
        models=["model-0", "model-1"],
        category_codes=["correccio"],
    )
    assert len(_load_prompts_and_responses(session, "correccio")) == 2
    assert clear_mock_tasks(session, version=DEFAULT_VERSION) == 1
    assert [p.id for p, _ in _load_prompts_and_responses(session, "correccio")] == [real.id]


@pytest.mark.parametrize("endpoint", ["/api/vote", "/api/task/skip"])
def test_replaced_task_cannot_be_resolved(client, session, logged_in_user, make_prompt, endpoint):
    user = logged_in_user("obsolete@example.com")
    old, responses = make_prompt("correccio_1", "v1")
    token = create_task_token(
        old.id,
        responses[0].id,
        responses[1].id,
        user.id,
        vote_after=datetime.now(UTC) - timedelta(seconds=1),
    )
    new, _ = make_prompt("correccio_1", "v2")
    payload = {"token": token}
    if endpoint == "/api/vote":
        payload["winner"] = "a"
    response = client.post(endpoint, json=payload)
    assert response.status_code == 410
    assert client.get("/api/task").json()["prompt"] == new.text
    assert session.scalar(select(func.count()).select_from(Vote)) == 0
    assert session.scalar(select(func.count()).select_from(TaskSkip)) == 0
