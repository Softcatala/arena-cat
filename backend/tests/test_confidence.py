"""Tests de `app.ranking.confidence.assess_confidence`.

Comprovem que el bootstrap clusteritzat amb etiquetes fixes és calibrat:
declara estable un rànquing realment estable i rebutja un cas de coin-flip.
"""

from __future__ import annotations

from sqlalchemy import select

from app.models import Category, Prompt, Response, Vote, Winner
from app.ranking.confidence import assess_confidence

MODELS = ["gemma-3-4b-it", "qwen-3.5-9b", "salamandra-7b-instruct"]


def _category(session, code="correccio"):
    return session.scalar(select(Category).where(Category.code == code))


def _seed_prompts(session, category_code, n_prompts):
    cat = _category(session, category_code)
    out = []
    for i in range(n_prompts):
        prompt = Prompt(
            version="vtest",
            code=f"{category_code}-conf-{i:02d}",
            category_id=cat.id,
            text=f"Prompt {i}",
        )
        session.add(prompt)
        session.flush()
        responses = {}
        for m in MODELS:
            r = Response(prompt=prompt, model=m, text=f"Resposta de {m}")
            session.add(r)
            responses[m] = r
        session.flush()
        out.append((prompt, responses))
    return out


def _vote(session, prompt, response_a, response_b, winner):
    session.add(
        Vote(
            prompt_id=prompt.id,
            response_a_id=response_a.id,
            response_b_id=response_b.id,
            winner=winner,
        )
    )


def test_assess_confidence_empty_category(session):
    """Sense vots, retorna valors per defecte amb is_stable=False."""
    result = assess_confidence(session, "correccio")
    assert result["best_model"] is None
    assert result["n_decisive_votes"] == 0
    assert result["is_stable"] is False


def test_assess_confidence_clear_winner_is_stable(session):
    """Si gemma guanya sempre, el rànquing és estable amb alta confiança."""
    prompts = _seed_prompts(session, "correccio", n_prompts=5)
    gemma, qwen, salamandra = MODELS
    for prompt, r in prompts:
        # gemma guanya 8 vegades cada parella que l'inclou.
        for _ in range(8):
            _vote(session, prompt, r[gemma], r[qwen], Winner.a)
            _vote(session, prompt, r[gemma], r[salamandra], Winner.a)
        # qwen vs salamandra: 4-4, no aporta direcció.
        for _ in range(4):
            _vote(session, prompt, r[qwen], r[salamandra], Winner.a)
            _vote(session, prompt, r[qwen], r[salamandra], Winner.b)

    # Bootstrap rapid per als tests (200 repliques en lloc de 1000).
    result = assess_confidence(session, "correccio", n_bootstrap=200, seed=42)
    assert result["best_model"] == gemma
    assert result["p_best_is_best"] >= 0.95
    assert result["is_stable"] is True
    assert result["ci_lo"] > 0


def test_assess_confidence_coin_flip_is_unstable(session):
    """Si totes les parelles són 50/50, el rànquing no és estable."""
    prompts = _seed_prompts(session, "traduccio", n_prompts=5)
    gemma, qwen, salamandra = MODELS
    for prompt, r in prompts:
        # 6-6 per a cada parella → veredicte real és tie.
        for _ in range(6):
            _vote(session, prompt, r[gemma], r[qwen], Winner.a)
            _vote(session, prompt, r[gemma], r[qwen], Winner.b)
            _vote(session, prompt, r[gemma], r[salamandra], Winner.a)
            _vote(session, prompt, r[gemma], r[salamandra], Winner.b)
            _vote(session, prompt, r[qwen], r[salamandra], Winner.a)
            _vote(session, prompt, r[qwen], r[salamandra], Winner.b)

    result = assess_confidence(session, "traduccio", n_bootstrap=200, seed=42)
    # El best és arbitrari (sampling noise), però el rànquing NO ha de ser estable.
    assert result["is_stable"] is False
    # ci_lo hauria de ser proper a zero o negatiu.
    assert result["ci_lo"] <= 0.05


def test_assess_confidence_ignores_ties_and_neither(session):
    """Empats i neithers no contribueixen al bootstrap BT."""
    prompts = _seed_prompts(session, "reformulacio", n_prompts=2)
    gemma, qwen, salamandra = MODELS
    for prompt, r in prompts:
        # 4 decisius (gemma guanya), més 5 empats i 3 neithers que han d'ignorar-se.
        for _ in range(4):
            _vote(session, prompt, r[gemma], r[qwen], Winner.a)
            _vote(session, prompt, r[gemma], r[salamandra], Winner.a)
            _vote(session, prompt, r[qwen], r[salamandra], Winner.a)
        for _ in range(5):
            _vote(session, prompt, r[gemma], r[qwen], Winner.tie)
        for _ in range(3):
            _vote(session, prompt, r[gemma], r[qwen], Winner.neither)

    result = assess_confidence(session, "reformulacio", n_bootstrap=200, seed=42)
    # 3 parelles × 4 decisius × 2 prompts = 24 vots decisius.
    assert result["n_decisive_votes"] == 24
