"""Prova de competència, acreditació persistent i protecció dels vots."""

from collections import Counter

import pytest
import yaml
from sqlalchemy import func, select

from app.models import Prompt, Response, TaskSkip, User, Vote
from tests.conftest import DEFAULT_PASSWORD, REPO_ROOT
from tests.test_vote_api import ready_task_token


@pytest.fixture
def questionnaire():
    return yaml.safe_load((REPO_ROOT / "data/qualification.yaml").read_text())


@pytest.fixture
def unqualified_user(client, session, login):
    email = "qualification@example.com"
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": DEFAULT_PASSWORD, "consent": True},
    )
    assert response.status_code == 200
    login(email)
    return session.scalar(select(User).where(User.email == email))


def answers_for(questionnaire, score):
    """Prepara un intent amb el nombre d'encerts indicat."""
    return {
        question["id"]: question["correct_answer"]
        if index < score
        else next(option for option in question["options"] if option != question["correct_answer"])
        for index, question in enumerate(questionnaire["questions"])
    }


@pytest.mark.parametrize("method", ["get", "post"])
def test_qualification_requires_session(client, questionnaire, method):
    kwargs = {"json": {"answers": answers_for(questionnaire, 10)}} if method == "post" else {}
    assert getattr(client, method)("/api/qualification", **kwargs).status_code == 401


def test_questionnaire_has_ten_questions_without_solutions(client, unqualified_user):
    response = client.get("/api/qualification")
    assert response.status_code == 200
    data = response.json()
    assert data["min_correct"] == 8
    assert Counter(q["category_code"] for q in data["questions"]) == {
        "correccio": 2,
        "traduccio": 2,
        "reformulacio": 2,
        "generacio": 2,
        None: 2,
    }
    for question in data["questions"]:
        assert set(question) == {"id", "category_code", "prompt", "options"}
        assert set(question["options"]) == {"A", "B", "C"}
    assert client.get("/api/auth/session").json()["qualified"] is False


@pytest.mark.parametrize("score,passed", [(7, False), (8, True), (10, True)])
def test_qualification_returns_only_total_without_solutions(
    client, session, unqualified_user, questionnaire, score, passed
):
    response = client.post(
        "/api/qualification", json={"answers": answers_for(questionnaire, score)}
    )
    assert response.status_code == 200
    result = response.json()
    assert result == {
        "score": score,
        "total": 10,
        "min_correct": 8,
        "passed": passed,
    }
    session.refresh(unqualified_user)
    assert (unqualified_user.qualified_at is not None) is passed
    assert client.get("/api/auth/session").json()["qualified"] is passed
    assert session.scalar(select(func.count()).select_from(Vote)) == 0
    assert session.scalar(select(func.count()).select_from(TaskSkip)) == 0
    assert client.get("/api/ranking").json()["n_votes_total"] == 0


def test_retry_and_qualification_survive_login(
    client, session, unqualified_user, questionnaire, login
):
    assert (
        client.post("/api/qualification", json={"answers": answers_for(questionnaire, 7)}).json()[
            "passed"
        ]
        is False
    )
    assert (
        client.post("/api/qualification", json={"answers": answers_for(questionnaire, 8)}).json()[
            "passed"
        ]
        is True
    )
    session.refresh(unqualified_user)
    qualified_at = unqualified_user.qualified_at
    client.post("/api/auth/logout")
    login(unqualified_user.email)
    assert client.get("/api/auth/session").json()["qualified"] is True
    assert client.get("/api/auth/export").json()["user"]["qualified_at"] is not None
    assert (
        client.post(
            "/api/qualification", json={"answers": answers_for(questionnaire, 10)}
        ).status_code
        == 409
    )
    session.refresh(unqualified_user)
    assert unqualified_user.qualified_at == qualified_at


@pytest.mark.parametrize("invalid", ["missing", "extra", "invalid_option", "multiple", "forged"])
def test_invalid_submission_does_not_qualify(
    client, session, unqualified_user, questionnaire, invalid
):
    answers = answers_for(questionnaire, 10)
    first = next(iter(answers))
    payload = {"answers": answers}
    if invalid == "missing":
        del answers[first]
    elif invalid == "extra":
        answers["invented"] = "A"
    elif invalid == "invalid_option":
        answers[first] = "D"
    elif invalid == "multiple":
        answers[first] = ["A", "B", "C"]
    else:
        payload["passed"] = True
    assert client.post("/api/qualification", json=payload).status_code == 422
    session.refresh(unqualified_user)
    assert unqualified_user.qualified_at is None


def test_threshold_is_read_from_yaml(
    client, unqualified_user, questionnaire, tmp_path, monkeypatch
):
    from app.services import qualification_service

    path = tmp_path / "qualification.yaml"
    monkeypatch.setattr(qualification_service, "QUALIFICATION_FILE", path)
    questionnaire["min_correct"] = 10
    path.write_text(yaml.safe_dump(questionnaire))
    assert client.get("/api/qualification").json()["min_correct"] == 10
    payload = {"answers": answers_for(questionnaire, 9)}
    assert client.post("/api/qualification", json=payload).json()["passed"] is False
    questionnaire["min_correct"] = 9
    path.write_text(yaml.safe_dump(questionnaire))
    assert client.post("/api/qualification", json=payload).json()["passed"] is True


def test_direct_vote_requires_qualification(client, session, unqualified_user, questionnaire):
    prompt = Prompt(version="v1", code="qualification-vote", category_id=1, text="Un text")
    session.add(prompt)
    session.flush()
    a = Response(prompt_id=prompt.id, model="a", text="A")
    b = Response(prompt_id=prompt.id, model="b", text="B")
    session.add_all([a, b])
    session.commit()
    token = ready_task_token(prompt.id, a.id, b.id, unqualified_user.id)
    payload = {"winner": "a", "token": token}
    assert client.post("/api/vote", json=payload).status_code == 403
    assert client.get("/api/task").status_code == 403
    assert client.post("/api/task/skip", json={"token": token}).status_code == 403
    assert session.scalar(select(func.count()).select_from(Vote)) == 0
    assert (
        client.post("/api/qualification", json={"answers": answers_for(questionnaire, 8)}).json()[
            "passed"
        ]
        is True
    )
    assert client.get("/api/task").status_code == 200
    assert client.post("/api/vote", json=payload).status_code == 200
    assert session.scalar(select(func.count()).select_from(Vote)) == 1
