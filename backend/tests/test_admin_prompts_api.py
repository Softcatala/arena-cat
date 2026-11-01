"""Gestió de prompts des de l'administració: alta, llistat i baixa."""

import hashlib

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Category, Prompt, Response

NEW_PROMPT = {
    "version": "v1",
    "code": "correccio_90",
    "category_code": "correccio",
    "text": "Corregeix aquest text.",
}


def add_prompt(session, code="correccio_91", version="v1", text="Un altre text.", responses=0):
    category = session.scalar(select(Category).where(Category.code == "correccio"))
    prompt = Prompt(version=version, code=code, category_id=category.id, text=text)
    session.add(prompt)
    session.flush()
    for index in range(responses):
        session.add(Response(prompt_id=prompt.id, model=f"model-{index}", text="Resposta"))
    session.commit()
    return prompt


def test_prompt_endpoints_require_an_admin(client, logged_in_user):
    logged_in_user("regular@example.com")
    assert client.get("/api/admin/prompts").status_code == 403
    assert client.post("/api/admin/prompts", json=NEW_PROMPT).status_code == 403
    assert client.delete("/api/admin/prompts/1").status_code == 403


def test_prompt_endpoints_require_a_session(client):
    assert client.get("/api/admin/prompts").status_code == 401
    assert client.post("/api/admin/prompts", json=NEW_PROMPT).status_code == 401
    assert client.delete("/api/admin/prompts/1").status_code == 401


def test_create_prompt_stores_the_sha256_of_its_text(client, admin, session):
    result = client.post("/api/admin/prompts", json=NEW_PROMPT)

    assert result.status_code == 201
    body = result.json()
    assert body["content_sha256"] == hashlib.sha256(b"Corregeix aquest text.").hexdigest()
    assert body["category_code"] == "correccio"
    assert body["response_count"] == 0
    stored = session.get(Prompt, body["id"])
    assert (stored.version, stored.code) == ("v1", "correccio_90")


def test_create_prompt_strips_the_text_before_hashing(client, admin):
    result = client.post("/api/admin/prompts", json={**NEW_PROMPT, "text": "  Hola.\n\n"})

    assert result.json()["text"] == "Hola."
    assert result.json()["content_sha256"] == hashlib.sha256(b"Hola.").hexdigest()


def test_create_rejects_a_duplicate_content(client, admin, session):
    existing = add_prompt(session, text="Corregeix aquest text.")

    result = client.post("/api/admin/prompts", json=NEW_PROMPT)

    assert result.status_code == 409
    assert str(existing.id) in result.json()["detail"]


def test_create_allows_the_same_content_in_a_new_version(client, admin, session):
    add_prompt(session, version="v1", text="Corregeix aquest text.")

    result = client.post("/api/admin/prompts", json={**NEW_PROMPT, "version": "v2"})

    assert result.status_code == 201


def test_create_rejects_a_duplicate_version_and_code(client, admin, session):
    add_prompt(session, code="correccio_90", text="Un text diferent.")

    result = client.post("/api/admin/prompts", json=NEW_PROMPT)

    assert result.status_code == 409


def test_create_rejects_an_unknown_category(client, admin):
    result = client.post("/api/admin/prompts", json={**NEW_PROMPT, "category_code": "inexistent"})

    assert result.status_code == 422


@pytest.mark.parametrize(
    "overrides",
    [
        {"version": "1"},
        {"version": "v0"},
        {"code": "Correcció 1"},
        {"code": ""},
        {"text": "   "},
        {"text": ""},
    ],
)
def test_create_validates_the_fields(client, admin, overrides):
    result = client.post("/api/admin/prompts", json={**NEW_PROMPT, **overrides})

    assert result.status_code == 422


def test_list_prompts_with_response_counts(client, admin, session):
    add_prompt(session, code="correccio_91", responses=2)
    add_prompt(session, code="correccio_92", text="Un altre.", responses=0)

    result = client.get("/api/admin/prompts")

    assert result.status_code == 200
    prompts = {prompt["code"]: prompt for prompt in result.json()["prompts"]}
    assert prompts["correccio_91"]["response_count"] == 2
    assert prompts["correccio_92"]["response_count"] == 0
    assert result.json()["total"] == 2


def test_list_prompts_filters_and_paginates(client, admin, session):
    add_prompt(session, code="correccio_91", version="v1", text="a")
    add_prompt(session, code="correccio_92", version="v2", text="b")
    add_prompt(session, code="correccio_93", version="v2", text="c")

    only_v2 = client.get("/api/admin/prompts", params={"version": "v2"}).json()
    page = client.get("/api/admin/prompts", params={"limit": 1, "offset": 1}).json()

    assert [prompt["code"] for prompt in only_v2["prompts"]] == ["correccio_92", "correccio_93"]
    assert only_v2["total"] == 2
    assert len(page["prompts"]) == 1
    assert page["total"] == 3


def test_delete_prompt_without_inferences(client, admin, session):
    prompt = add_prompt(session)

    result = client.delete(f"/api/admin/prompts/{prompt.id}")

    assert result.status_code == 204
    assert session.get(Prompt, prompt.id) is None


def test_delete_prompt_with_inferences_is_refused(client, admin, session):
    prompt = add_prompt(session, responses=2)

    result = client.delete(f"/api/admin/prompts/{prompt.id}")

    assert result.status_code == 409
    assert session.get(Prompt, prompt.id) is not None
    assert len(session.scalars(select(Response)).all()) == 2


def test_delete_unknown_prompt_is_not_found(client, admin):
    assert client.delete("/api/admin/prompts/999999").status_code == 404


def test_database_rejects_a_duplicate_hash_in_a_version(session):
    add_prompt(session, code="correccio_91", text="Repetit")

    with pytest.raises(IntegrityError):
        add_prompt(session, code="correccio_92", text="Repetit")
    session.rollback()


# ---------------------------------------------------------------------------
# Activació de prompts.
# ---------------------------------------------------------------------------


def serve_text(client):
    """Text del prompt de la tasca servida, o None si no n'hi ha cap."""
    result = client.get("/api/task")
    return result.json()["prompt"] if result.status_code == 200 else None


def test_new_prompts_are_active(client, admin):
    result = client.post("/api/admin/prompts", json=NEW_PROMPT)

    assert result.json()["active"] is True


def test_patch_prompt_toggles_the_flag(client, admin, session):
    prompt = add_prompt(session)

    off = client.patch(f"/api/admin/prompts/{prompt.id}", json={"active": False})
    on = client.patch(f"/api/admin/prompts/{prompt.id}", json={"active": True})

    assert off.status_code == 200
    assert off.json()["active"] is False
    assert on.json()["active"] is True
    assert on.json()["category_code"] == "correccio"


def test_patch_prompt_requires_the_field(client, admin, session):
    prompt = add_prompt(session)

    assert client.patch(f"/api/admin/prompts/{prompt.id}", json={}).status_code == 422


def test_patch_unknown_prompt(client, admin):
    assert client.patch("/api/admin/prompts/999999", json={"active": False}).status_code == 404


def test_patch_prompt_requires_an_admin(client, logged_in_user):
    logged_in_user("regular@example.com")

    assert client.patch("/api/admin/prompts/1", json={"active": False}).status_code == 403


def test_list_prompts_can_filter_by_active(client, admin, session):
    add_prompt(session, code="correccio_91", text="a")
    off = add_prompt(session, code="correccio_92", text="b")
    off.active = False
    session.commit()

    inactive = client.get("/api/admin/prompts", params={"active": "false"}).json()

    assert [prompt["code"] for prompt in inactive["prompts"]] == ["correccio_92"]
    assert inactive["total"] == 1


def test_inactive_prompt_is_not_served(client, admin, session):
    prompt = add_prompt(session, responses=2, text="Prompt únic")
    assert serve_text(client) == "Prompt únic"

    client.patch(f"/api/admin/prompts/{prompt.id}", json={"active": False})

    assert serve_text(client) is None


def test_deactivating_the_newest_version_falls_back_to_the_previous_one(client, admin, session):
    add_prompt(session, code="correccio_91", version="v1", text="Versió antiga", responses=2)
    newest = add_prompt(session, code="correccio_91", version="v2", text="Versió nova", responses=2)
    assert serve_text(client) == "Versió nova"

    client.patch(f"/api/admin/prompts/{newest.id}", json={"active": False})

    assert serve_text(client) == "Versió antiga"

    client.patch(f"/api/admin/prompts/{newest.id}", json={"active": True})

    assert serve_text(client) == "Versió nova"


def test_deactivating_a_prompt_removes_its_votes_from_the_ranking(client, admin, session):
    from app.models import Vote, Winner

    prompt = add_prompt(session, responses=2, text="Prompt amb vots")
    first, second = session.scalars(select(Response).where(Response.prompt_id == prompt.id)).all()
    session.add(
        Vote(
            prompt_id=prompt.id,
            response_a_id=first.id,
            response_b_id=second.id,
            winner=Winner.a,
        )
    )
    session.commit()
    assert client.get("/api/ranking").json()["n_votes_total"] == 1

    client.patch(f"/api/admin/prompts/{prompt.id}", json={"active": False})

    assert client.get("/api/ranking").json()["n_votes_total"] == 0

    client.patch(f"/api/admin/prompts/{prompt.id}", json={"active": True})

    assert client.get("/api/ranking").json()["n_votes_total"] == 1
