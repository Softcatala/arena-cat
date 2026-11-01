"""Importació d'inferències des de fitxers YAML de la canonada d'inferència."""

import hashlib
import sys
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models import Category, Prompt, Response

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import carrega_inferencies as loader  # noqa: E402

PROMPT_TEXT = "Corregeix aquest text."


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def make_yaml(
    code="correccio_90",
    model="model-a",
    answer="Una resposta.",
    prompt_sha=None,
    extra="",
) -> str:
    prompt_sha = sha(PROMPT_TEXT + "\n") if prompt_sha is None else prompt_sha
    return (
        "backend:\n  engine: transformers\n"
        "generation:\n  seed: 42\n  temperature: 0.7\n"
        f"model:\n  id: {model}\n  model_name: Org/{model}\n  revision: main\n"
        f"output:\n  answer: {answer}\n"
        f"prompt:\n  id: {code}\n  sha256: {prompt_sha}\n"
        "reasoning:\n  content: null\n"
        f"{extra}"
    )


def upload(client, files, version="v1"):
    body = {"version": version, "files": [{"name": n, "content": c} for n, c in files]}
    return client.post("/api/admin/responses/import", json=body)


@pytest.fixture
def prompt(session) -> Prompt:
    category = session.scalar(select(Category).where(Category.code == "correccio"))
    prompt = Prompt(version="v1", code="correccio_90", category_id=category.id, text=PROMPT_TEXT)
    session.add(prompt)
    session.commit()
    return prompt


def test_import_requires_a_session(client):
    assert upload(client, [("a.yaml", make_yaml())]).status_code == 401


def test_import_requires_an_admin(client, logged_in_user):
    logged_in_user("regular@example.com")

    assert upload(client, [("a.yaml", make_yaml())]).status_code == 403


def test_import_inserts_the_response_with_its_metadata(client, admin, session, prompt):
    result = upload(client, [("a.yaml", make_yaml(answer="  Resposta nova.  "))])

    assert result.status_code == 200
    body = result.json()
    assert (body["inserted"], body["skipped"], body["errors"]) == (1, 0, 0)
    assert body["files"] == [{"name": "a.yaml", "status": "inserted", "detail": None}]
    stored = session.scalar(select(Response).where(Response.prompt_id == prompt.id))
    assert stored.model == "model-a"
    assert stored.text == "Resposta nova."
    assert stored.active is True
    assert stored.inference_metadata["generation"] == {"seed": 42, "temperature": 0.7}
    assert stored.inference_metadata["model_name"] == "Org/model-a"


def test_reimporting_the_same_file_is_skipped(client, admin, session, prompt):
    upload(client, [("a.yaml", make_yaml())])

    body = upload(client, [("a.yaml", make_yaml())]).json()

    assert (body["inserted"], body["skipped"], body["errors"]) == (0, 1, 0)
    assert len(session.scalars(select(Response)).all()) == 1


def test_a_changed_answer_is_an_error_and_keeps_the_original(client, admin, session, prompt):
    upload(client, [("a.yaml", make_yaml(answer="Original."))])

    body = upload(client, [("a.yaml", make_yaml(answer="Canviada."))]).json()

    assert body["errors"] == 1
    assert body["files"][0]["status"] == "error"
    assert session.scalar(select(Response.text)) == "Original."


def test_unknown_prompt_is_an_error_but_other_files_are_imported(client, admin, session, prompt):
    files = [("a.yaml", make_yaml(code="no_existeix_1")), ("b.yaml", make_yaml(model="model-b"))]

    body = upload(client, files).json()

    assert (body["inserted"], body["errors"]) == (1, 1)
    statuses = {item["name"]: item for item in body["files"]}
    assert statuses["a.yaml"]["status"] == "error"
    assert "no_existeix_1" in statuses["a.yaml"]["detail"]
    assert statuses["b.yaml"]["status"] == "inserted"


def test_prompt_is_looked_up_in_the_requested_version(client, admin, session, prompt):
    body = upload(client, [("a.yaml", make_yaml())], version="v2").json()

    assert body["errors"] == 1
    assert session.scalars(select(Response)).all() == []


@pytest.mark.parametrize("suffix", ["", "\n", "\n\n", "   \n", "  \n\n"])
def test_prompt_hash_accepts_the_raw_file_endings(client, admin, session, prompt, suffix):
    content = make_yaml(prompt_sha=sha(PROMPT_TEXT + suffix))

    assert upload(client, [("a.yaml", content)]).json()["inserted"] == 1


def test_prompt_hash_rejects_other_trailing_characters(client, admin, session, prompt):
    content = make_yaml(prompt_sha=sha(PROMPT_TEXT + " x\n"))

    assert upload(client, [("a.yaml", content)]).json()["errors"] == 1


def test_prompt_hash_mismatch_is_an_error(client, admin, session, prompt):
    content = make_yaml(prompt_sha=sha("Un altre text del prompt"))

    body = upload(client, [("a.yaml", content)]).json()

    assert body["errors"] == 1
    assert "hash" in body["files"][0]["detail"]
    assert session.scalars(select(Response)).all() == []


def test_a_file_without_a_prompt_hash_is_accepted(client, admin, session, prompt):
    content = make_yaml().replace(f"  sha256: {sha(PROMPT_TEXT + chr(10))}\n", "")

    assert upload(client, [("a.yaml", content)]).json()["inserted"] == 1


@pytest.mark.parametrize(
    "content",
    [
        "no: [valid",
        "- una\n- llista\n",
        "model:\n  id: m\noutput:\n  answer: x\n",
        "prompt:\n  id: correccio_90\noutput:\n  answer: x\n",
        "prompt:\n  id: correccio_90\nmodel:\n  id: m\n",
        "prompt:\n  id: correccio_90\nmodel:\n  id: m\noutput:\n  answer: '   '\n",
    ],
)
def test_invalid_files_are_reported_as_errors(client, admin, session, prompt, content):
    body = upload(client, [("a.yaml", content)]).json()

    assert (body["inserted"], body["errors"]) == (0, 1)
    assert body["files"][0]["detail"]


def test_import_validates_the_request(client, admin):
    assert upload(client, [("a.yaml", make_yaml())], version="1").status_code == 422
    assert upload(client, []).status_code == 422
    assert upload(client, [("a.yaml", "x" * 300_000)]).status_code == 422
    too_many = [(f"{index}.yaml", make_yaml()) for index in range(201)]
    assert upload(client, too_many).status_code == 422


def test_parsing_matches_the_command_line_loader(client, admin, session, prompt, tmp_path):
    content = make_yaml(answer="Resposta de prova.", extra="run:\n  device: cuda\n")
    path = tmp_path / "a.yaml"
    path.write_text(content, encoding="utf-8")
    expected = loader.parse_inference_file(path, "v1")

    upload(client, [("a.yaml", content)])

    stored = session.scalar(select(Response).where(Response.prompt_id == prompt.id))
    assert stored.model == expected.model
    assert stored.text == expected.text
    assert stored.inference_metadata == expected.metadata
