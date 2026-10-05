"""Consulta de totes les categories, revisions de prompts i respostes carregades."""

import pytest
from sqlalchemy import delete, select

from app.config import get_settings
from app.models import Category, Prompt, Response


@pytest.fixture(autouse=True)
def admin_token(monkeypatch):
    monkeypatch.setenv("ADMIN_API_TOKEN", "test-admin-token")
    get_settings.cache_clear()


@pytest.mark.parametrize(
    "authorization", [None, "Bearer wrong", "Basic test-admin-token", "Bearer "]
)
def test_dataset_rejects_invalid_token(client, authorization):
    headers = {"Authorization": authorization} if authorization else {}
    result = client.get("/api/dataset", headers=headers)
    assert result.status_code == 401
    assert result.headers["WWW-Authenticate"] == "Bearer"


def test_dataset_denies_access_when_token_is_unconfigured(client, monkeypatch):
    monkeypatch.setenv("ADMIN_API_TOKEN", "")
    get_settings.cache_clear()
    assert (
        client.get("/api/dataset", headers={"Authorization": "Bearer test-admin-token"}).status_code
        == 401
    )


def test_session_does_not_grant_dataset_access(client, logged_in_user):
    logged_in_user("dataset@example.com")
    assert client.get("/api/dataset").status_code == 401


def test_dataset_includes_all_versions_and_responses(client, session):
    category = session.scalar(select(Category).where(Category.code == "correccio"))
    prompts = [
        Prompt(code="correccio_1", version=version, category_id=category.id, text=version)
        for version in ("v1", "v2", "v10")
    ]
    session.add_all(prompts)
    session.flush()
    responses = [
        Response(prompt_id=prompts[0].id, model="model-a", text="Resposta antiga"),
        Response(
            prompt_id=prompts[1].id,
            model="model-b",
            text="Resposta nova",
            inference_metadata={"seed": 42},
        ),
    ]
    session.add_all(responses)
    session.flush()

    result = client.get("/api/dataset", headers={"Authorization": "Bearer test-admin-token"})

    assert result.status_code == 200
    assert result.headers["Cache-Control"] == "no-store"
    data = result.json()
    assert set(data) == {"categories", "prompts", "responses"}
    assert len(data["categories"]) == 4
    assert next(c for c in data["categories"] if c["id"] == category.id)["code"] == "correccio"
    assert [p["id"] for p in data["prompts"]] == [p.id for p in prompts]
    assert [p["version"] for p in data["prompts"]] == ["v1", "v2", "v10"]
    assert all(p["category_id"] == category.id for p in data["prompts"])
    assert [p["text"] for p in data["prompts"]] == ["v1", "v2", "v10"]
    assert [r["prompt_id"] for r in data["responses"]] == [prompts[0].id, prompts[1].id]
    assert [r["model"] for r in data["responses"]] == ["model-a", "model-b"]
    assert [r["text"] for r in data["responses"]] == ["Resposta antiga", "Resposta nova"]
    assert data["responses"][0]["inference_metadata"] is None
    assert data["responses"][1]["inference_metadata"] == {"seed": 42}


def test_dataset_returns_empty_lists(client, session):
    session.execute(delete(Category))
    result = client.get("/api/dataset", headers={"Authorization": "Bearer test-admin-token"})
    assert result.status_code == 200
    assert result.json() == {"categories": [], "prompts": [], "responses": []}
