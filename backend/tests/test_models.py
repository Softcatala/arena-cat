"""Tests del model de dades: relacions, unicitat, enums, restricció CHECK i índexs."""

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.models import Category, Prompt, Response, Vote, Winner


def _category(session, code="traduccio"):
    return session.scalar(select(Category).where(Category.code == code))


def _prompt_with_responses(session):
    """Crea un prompt amb dues respostes de models diferents i retorna (p, ra, rb)."""
    prompt = Prompt(
        version="v1",
        code="traduccio-01",
        category_id=_category(session).id,
        text="Tradueix aquest text al català en registre col·loquial.",
    )
    response_a = Response(prompt=prompt, model="salamandra-7b", text="Resposta del model A")
    response_b = Response(prompt=prompt, model="qwen-3.5-9b", text="Resposta del model B")
    session.add(prompt)
    session.flush()
    return prompt, response_a, response_b


def test_create_prompt_response_vote(session):
    prompt, response_a, response_b = _prompt_with_responses(session)

    vote = Vote(
        prompt=prompt,
        response_a_id=response_a.id,
        response_b_id=response_b.id,
        winner=Winner.a,
        session_id="sessio-anonima-123",
        response_time_s=12.5,
    )
    session.add(vote)
    session.flush()

    assert vote.id is not None
    # Navegació de relacions.
    assert len(prompt.responses) == 2
    assert response_a.prompt is prompt


def test_jsonb_metadata(session):
    prompt, _, _ = _prompt_with_responses(session)
    response = Response(
        prompt=prompt,
        model="gemma-4-26b",
        text="Una resposta amb metadades",
        inference_metadata={"seed": 42, "temperatura": 0.7, "top_p": 0.95, "quantization": "int4"},
    )
    session.add(response)
    session.flush()
    session.refresh(response)
    assert response.inference_metadata["seed"] == 42


def test_response_unique_per_prompt_and_model(session):
    prompt, _, _ = _prompt_with_responses(session)
    # Mateix prompt + mateix model que la resposta A ja existent → viola UNIQUE.
    session.add(Response(prompt=prompt, model="salamandra-7b", text="Duplicada"))
    with pytest.raises(IntegrityError):
        session.flush()


def test_prompt_unique_per_version_and_code(session):
    _prompt_with_responses(session)
    session.add(
        Prompt(
            version="v1",
            code="traduccio-01",
            category_id=_category(session, "correccio").id,
            text="Un altre text amb el mateix codi i versió",
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.parametrize("value", list(Winner))
def test_winner_accepts_valid_values(session, value):
    prompt, response_a, response_b = _prompt_with_responses(session)
    vote = Vote(
        prompt=prompt,
        response_a_id=response_a.id,
        response_b_id=response_b.id,
        winner=value,
    )
    session.add(vote)
    session.flush()
    assert vote.winner is value


def test_winner_rejects_invalid_value(session):
    prompt, response_a, response_b = _prompt_with_responses(session)
    # Inserció directa amb un valor fora de l'enum: la base de dades l'ha de rebutjar.
    with pytest.raises(DBAPIError):
        session.execute(
            text(
                "INSERT INTO votes (prompt_id, response_a_id, response_b_id, winner) "
                "VALUES (:p, :a, :b, 'valor_inexistent')"
            ),
            {"p": prompt.id, "a": response_a.id, "b": response_b.id},
        )


def test_nonexistent_category_is_rejected(session):
    prompt = Prompt(version="v1", code="x-01", category_id=999999, text="text")
    session.add(prompt)
    with pytest.raises(IntegrityError):
        session.flush()


def test_duplicate_category_code_is_rejected(session):
    session.add(Category(code="traduccio", name="Traducció", description="Una altra"))
    with pytest.raises(IntegrityError):
        session.flush()


def test_vote_with_equal_responses_is_rejected(session):
    prompt, response_a, _ = _prompt_with_responses(session)
    vote = Vote(
        prompt=prompt,
        response_a_id=response_a.id,
        response_b_id=response_a.id,  # mateixa resposta a A i B → viola el CHECK
        winner=Winner.tie,
    )
    session.add(vote)
    with pytest.raises(IntegrityError):
        session.flush()


def test_vote_with_response_from_another_prompt_is_rejected(session):
    prompt_a, response_a, _ = _prompt_with_responses(session)
    prompt_b = Prompt(
        version="v1",
        code="traduccio-02",
        category_id=_category(session).id,
        text="Un altre prompt.",
    )
    response_other = Response(
        prompt=prompt_b, model="gemma-4-26b", text="Resposta d'un altre prompt"
    )
    session.add(prompt_b)
    session.flush()

    # response_other és d'un altre prompt → viola la FK composta de votes.
    vote = Vote(
        prompt_id=prompt_a.id,
        response_a_id=response_a.id,
        response_b_id=response_other.id,
        winner=Winner.a,
    )
    session.add(vote)
    with pytest.raises(IntegrityError):
        session.flush()


def test_votes_indexes(engine):
    names = {idx["name"] for idx in inspect(engine).get_indexes("votes")}
    assert "ix_votes_prompt_id" in names
    assert "ix_votes_created_at" in names


def test_created_at_is_set_automatically(session):
    prompt, _, _ = _prompt_with_responses(session)
    session.refresh(prompt)
    assert prompt.created_at is not None
    assert prompt.created_at.tzinfo is not None  # és timestamptz
