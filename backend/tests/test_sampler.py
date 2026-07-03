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


def test_select_next_task_excludes_cells_voted_by_session(session):
    """Si una sessió ja ha votat una cel·la, no se li ha de tornar a oferir."""
    _seed_prompts(session, "correccio", n_prompts=2)
    # 2 prompts × 3 parelles = 6 cel·les en total.

    # Una sessió vota 3 cel·les concretes.
    session_id = "sessio-A"
    voted_cells: set[tuple[int, str, str]] = set()
    for _ in range(3):
        task = select_next_task(session, "correccio", session_id=session_id, seed=_)
        assert task is not None
        ra = session.get(Response, task["response_a_id"])
        rb = session.get(Response, task["response_b_id"])
        voted_cells.add((task["prompt_id"], *sorted((ra.model, rb.model))))
        session.add(
            Vote(
                prompt_id=task["prompt_id"],
                response_a_id=task["response_a_id"],
                response_b_id=task["response_b_id"],
                winner=Winner.a,
                session_id=session_id,
            )
        )
        session.flush()

    assert len(voted_cells) == 3  # cap repetició entre els 3 vots

    # Les properes crides amb la MATEIXA sessió no han de retornar cap de les 3 cel·les ja votades.
    for i in range(5):
        task = select_next_task(session, "correccio", session_id=session_id, seed=100 + i)
        assert task is not None
        ra = session.get(Response, task["response_a_id"])
        rb = session.get(Response, task["response_b_id"])
        cell = (task["prompt_id"], *sorted((ra.model, rb.model)))
        assert cell not in voted_cells, f"Sampler ha tornat a oferir {cell} a {session_id}"


def test_select_next_task_returns_none_when_session_completes_category(session):
    """Quan una sessió ha votat totes les cel·les, la funció retorna None."""
    _seed_prompts(session, "traduccio", n_prompts=1)
    # 1 prompt × 3 parelles = 3 cel·les.

    session_id = "sessio-completa"
    # Votem cada cel·la una vegada des de la mateixa sessió.
    for i in range(3):
        task = select_next_task(session, "traduccio", session_id=session_id, seed=i)
        assert task is not None
        session.add(
            Vote(
                prompt_id=task["prompt_id"],
                response_a_id=task["response_a_id"],
                response_b_id=task["response_b_id"],
                winner=Winner.a,
                session_id=session_id,
            )
        )
        session.flush()

    # Quarta crida: ja no queden cel·les noves per a aquesta sessió.
    task = select_next_task(session, "traduccio", session_id=session_id, seed=999)
    assert task is None


def test_select_next_task_different_sessions_are_independent(session):
    """Una sessió A no afecta el que veu una sessió B."""
    _seed_prompts(session, "reformulacio", n_prompts=1)
    # Sessió A vota totes les 3 cel·les.
    for i in range(3):
        task = select_next_task(session, "reformulacio", session_id="sessio-A", seed=i)
        assert task is not None
        session.add(
            Vote(
                prompt_id=task["prompt_id"],
                response_a_id=task["response_a_id"],
                response_b_id=task["response_b_id"],
                winner=Winner.a,
                session_id="sessio-A",
            )
        )
        session.flush()

    # Sessió A ja no pot votar més.
    assert select_next_task(session, "reformulacio", session_id="sessio-A", seed=0) is None
    # Sessió B sí pot votar — encara no ha vist cap cel·la.
    task_b = select_next_task(session, "reformulacio", session_id="sessio-B", seed=0)
    assert task_b is not None
