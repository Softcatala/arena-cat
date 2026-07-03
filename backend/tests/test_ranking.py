"""Tests de `app.ranking.ranking.compute_ranking`.

Inserim vots sintètics a la base de dades de tests i comprovem que la
funció pública retorna les peces esperades: comptes correctes, BT sensible,
matriu bruta coherent, detecció de cicles.
"""

from __future__ import annotations

from sqlalchemy import select

from app.models import Category, Prompt, Response, Vote, Winner
from app.ranking.ranking import compute_ranking, fit_bt

# ---------------------------------------------------------------------------
# Helpers per construir l'estat de la base de dades.
# ---------------------------------------------------------------------------


MODELS = ["gemma-3-4b-it", "qwen-3.5-9b", "salamandra-7b-instruct"]


def _category(session, code="correccio") -> Category:
    return session.scalar(select(Category).where(Category.code == code))


def _seed_prompts(session, category_code: str, n_prompts: int) -> list[tuple[Prompt, dict]]:
    """Crea n_prompts dins d'una categoria, cadascun amb una resposta per model."""
    cat = _category(session, category_code)
    results = []
    for i in range(n_prompts):
        prompt = Prompt(
            version="vtest",
            code=f"{category_code}-{i:02d}",
            category_id=cat.id,
            text=f"Prompt {i} a {category_code}",
        )
        session.add(prompt)
        session.flush()
        responses_by_model = {}
        for m in MODELS:
            r = Response(prompt=prompt, model=m, text=f"Resposta de {m} a {prompt.code}")
            session.add(r)
            responses_by_model[m] = r
        session.flush()
        results.append((prompt, responses_by_model))
    return results


def _record_vote(
    session,
    prompt: Prompt,
    response_a: Response,
    response_b: Response,
    winner: Winner,
) -> None:
    """Insereix un vot."""
    session.add(
        Vote(
            prompt_id=prompt.id,
            response_a_id=response_a.id,
            response_b_id=response_b.id,
            winner=winner,
        )
    )


def _plant_winner(
    session,
    category_code: str,
    winning_model: str,
    n_prompts: int = 4,
    decisive_per_pair_per_prompt: int = 8,
) -> None:
    """Insereix vots que fan que `winning_model` sigui clarament el millor.

    Per a cada parella que inclou el guanyador, registra `decisive_per_pair_per_prompt`
    vots a favor seu i 0 a favor de l'altre. Per a la parella sense el guanyador,
    reparteix els vots 50/50 perquè no influeixin al rànquing.
    """
    prompts = _seed_prompts(session, category_code, n_prompts)
    for prompt, responses in prompts:
        for model_a, model_b in [
            (MODELS[0], MODELS[1]),
            (MODELS[0], MODELS[2]),
            (MODELS[1], MODELS[2]),
        ]:
            for _ in range(decisive_per_pair_per_prompt):
                if winning_model in (model_a, model_b):
                    winner = Winner.a if model_a == winning_model else Winner.b
                else:
                    winner = Winner.a  # 50/50 entre no-guanyadors es resol arbitràriament
                _record_vote(session, prompt, responses[model_a], responses[model_b], winner)


# ---------------------------------------------------------------------------
# fit_bt aïllat (sense base de dades).
# ---------------------------------------------------------------------------


def test_fit_bt_with_empty_votes_returns_zeros():
    """Sense vots, tots els skills són zero."""
    skills = fit_bt([], ["a", "b", "c"])
    assert skills == {"a": 0.0, "b": 0.0, "c": 0.0}


def test_fit_bt_recovers_clear_winner():
    """Si A guanya sempre, A té el skill més alt."""
    decisive = [("a", "b")] * 50 + [("a", "c")] * 50 + [("b", "c")] * 25 + [("c", "b")] * 25
    skills = fit_bt(decisive, ["a", "b", "c"])
    assert skills["a"] > skills["b"]
    assert skills["a"] > skills["c"]
    # Sum-to-zero per identificabilitat.
    assert abs(sum(skills.values())) < 1e-6


def test_fit_bt_handles_complete_separation():
    """A guanya 100% a B; la regularització evita divergència."""
    decisive = [("a", "b")] * 100
    skills = fit_bt(decisive, ["a", "b"], alpha=0.01)
    # Sense regularització, theta_a − theta_b divergiria; amb regularització és finit.
    assert all(abs(s) < 10.0 for s in skills.values())
    assert skills["a"] > skills["b"]


# ---------------------------------------------------------------------------
# compute_ranking — escenaris bàsics.
# ---------------------------------------------------------------------------


def test_compute_ranking_empty_category(session):
    """Sense vots, la sortida és coherent amb valors per defecte."""
    result = compute_ranking(session, "correccio")
    assert result["category_code"] == "correccio"
    assert result["n_votes_total"] == 0
    assert result["best_model"] is None
    assert result["bt_skills"] == {}
    assert result["raw_pairwise"] == []
    assert result["cycle_detected"] is False


def test_compute_ranking_identifies_clear_winner(session):
    """Si plantem gemma com a guanyadora clara, ha de ser el millor."""
    _plant_winner(session, "correccio", winning_model="gemma-3-4b-it")
    result = compute_ranking(session, "correccio")
    assert result["best_model"] == "gemma-3-4b-it"
    # Els BT skills sumen zero.
    assert abs(sum(result["bt_skills"].values())) < 1e-3
    # gemma té el skill més alt.
    skills = result["bt_skills"]
    assert skills["gemma-3-4b-it"] > skills["qwen-3.5-9b"]
    assert skills["gemma-3-4b-it"] > skills["salamandra-7b-instruct"]


def test_compute_ranking_counts_ties_and_neither(session):
    """Els empats i els 'neither' es reporten per separat i no entren a BT."""
    prompts = _seed_prompts(session, "traduccio", n_prompts=1)
    prompt, responses = prompts[0]
    a, b = responses[MODELS[0]], responses[MODELS[1]]
    # 3 decisius (A guanya), 2 empats, 1 neither.
    for _ in range(3):
        _record_vote(session, prompt, a, b, Winner.a)
    for _ in range(2):
        _record_vote(session, prompt, a, b, Winner.tie)
    _record_vote(session, prompt, a, b, Winner.neither)

    result = compute_ranking(session, "traduccio")
    assert result["n_votes_total"] == 6
    assert result["n_votes_decisive"] == 3
    assert result["n_ties"] == 2
    assert result["n_neither"] == 1


def test_compute_ranking_detects_cycle(session):
    """Si A>B, B>C, C>A en taxes brutes, marquem cicle."""
    a_model, b_model, c_model = MODELS  # gemma, qwen, salamandra
    prompts = _seed_prompts(session, "reformulacio", n_prompts=1)
    prompt, responses = prompts[0]
    # A guanya B (clarament).
    for _ in range(8):
        _record_vote(session, prompt, responses[a_model], responses[b_model], Winner.a)
    # B guanya C (clarament).
    for _ in range(8):
        _record_vote(session, prompt, responses[b_model], responses[c_model], Winner.a)
    # C guanya A (clarament).
    for _ in range(8):
        _record_vote(session, prompt, responses[c_model], responses[a_model], Winner.a)

    result = compute_ranking(session, "reformulacio")
    assert result["cycle_detected"] is True
    assert len(result["cycle_path"]) == 4  # path tancat: [A, B, C, A]
    assert result["cycle_path"][0] == result["cycle_path"][-1]


def test_compute_ranking_isolates_categories(session):
    """Els vots d'una categoria no contaminen el rànquing d'una altra."""
    _plant_winner(session, "correccio", winning_model="gemma-3-4b-it", n_prompts=2)
    _plant_winner(session, "traduccio", winning_model="salamandra-7b-instruct", n_prompts=2)

    r1 = compute_ranking(session, "correccio")
    r2 = compute_ranking(session, "traduccio")
    assert r1["best_model"] == "gemma-3-4b-it"
    assert r2["best_model"] == "salamandra-7b-instruct"


def test_compute_ranking_pairwise_keys_are_alphabetical(session):
    """A la matriu bruta, model_a < model_b alfabèticament."""
    _plant_winner(session, "correccio", winning_model="gemma-3-4b-it", n_prompts=1)
    result = compute_ranking(session, "correccio")
    for stat in result["raw_pairwise"]:
        assert stat["model_a"] < stat["model_b"]
