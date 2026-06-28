"""Tests de `app.ranking.sampler.select_next_task`."""

from __future__ import annotations

from collections import Counter

from sqlalchemy import select

from app.models import Category, Prompt, Response, Vote, Winner
from app.ranking.sampler import select_next_task

MODELS = ["gemma-3-4b-it", "qwen-3.5-9b", "salamandra-7b-instruct"]


def _category(session, code="correccio"):
    return session.scalar(select(Category).where(Category.code == code))


def _seed_prompts(session, category_code, n_prompts):
    cat = _category(session, category_code)
    out = []
    for i in range(n_prompts):
        prompt = Prompt(
            version="vtest",
            code=f"{category_code}-samp-{i:02d}",
            category_id=cat.id,
            text=f"Prompt {i} a {category_code}",
        )
        session.add(prompt)
        session.flush()
        responses = {}
        for m in MODELS:
            r = Response(prompt=prompt, model=m, text=f"Resposta de {m} a {prompt.code}")
            session.add(r)
            responses[m] = r
        session.flush()
        out.append((prompt, responses))
    return out


def test_select_next_task_returns_none_for_empty_category(session):
    """Sense prompts, la funció retorna None."""
    task = select_next_task(session, "correccio")
    assert task is None


def test_select_next_task_returns_well_formed_task(session):
    """La tasca conté el prompt, dues respostes diferents, sense identificar models."""
    _seed_prompts(session, "correccio", n_prompts=2)
    task = select_next_task(session, "correccio", seed=42)
    assert task is not None
    assert task["category_code"] == "correccio"
    assert task["prompt_id"] is not None
    assert task["response_a_id"] != task["response_b_id"]
    # Les claus 'model' NO han d'aparèixer — el frontend ha de veure les respostes a cegues.
    assert "model_a" not in task
    assert "model_b" not in task


def test_select_next_task_balances_cells(session):
    """Trucant la funció moltes vegades, els recomptes de cel·les són gairebé iguals."""
    _seed_prompts(session, "traduccio", n_prompts=2)

    # Simulem una campanya: cada cop, llegim la propera tasca i hi enregistrem un vot.
    counts: Counter = Counter()
    for i in range(30):
        task = select_next_task(session, "traduccio", seed=i)
        assert task is not None
        # Per comptar la cel·la, recuperem els models de les respostes.
        ra = session.get(Response, task["response_a_id"])
        rb = session.get(Response, task["response_b_id"])
        cell = (task["prompt_id"], *sorted((ra.model, rb.model)))
        counts[cell] += 1
        # Guardem el vot perquè la propera crida el vegi.
        session.add(
            Vote(
                prompt_id=task["prompt_id"],
                response_a_id=task["response_a_id"],
                response_b_id=task["response_b_id"],
                winner=Winner.a,
            )
        )
        session.flush()

    # 2 prompts × 3 parelles = 6 cel·les. Amb 30 vots, l'esperat és 5 per cel·la.
    # Quota-balanced ha de donar comptes propers (diferència ≤ 1).
    assert len(counts) == 6
    values = list(counts.values())
    assert max(values) - min(values) <= 1, f"Cell counts not balanced: {counts}"
    assert sum(values) == 30
