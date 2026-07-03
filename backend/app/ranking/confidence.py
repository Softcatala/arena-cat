"""Avalua la confiança del rànquing actual d'una categoria.

La funció `assess_confidence` respon a la tercera pregunta de la
tasca 7: hem arribat a prou avaluacions? Quina certesa tenim sobre el
millor model?

Mètode: bootstrap clusteritzat amb etiquetes fixes.

1. Ajustem BT sobre totes les dades per identificar el millor actual.
   Aquesta etiqueta queda CONGELADA per a totes les repliques.
2. Re-mostrejem prompts sencers AMB reemplaçament (cluster bootstrap)
   per respectar la dependència intra-prompt.
3. Per cada replica, ajustem BT i calculem `delta = θ[best_fix] − max(θ[competidor])`.
   El delta pot ser NEGATIU si en aquesta replica el millor perd.
4. Reportem `p_best_is_best` (fracció de deltas > 0) i el CI 95% (percentils
   2.5 i 97.5 dels deltas).

Regla d'aturada operativa: el rànquing és estable si `ci_lo > 0`.

Limitacions documentades a `docs/T7_ranking_design.md` §5.3:
- Bootstrap clusteritzat amb 10 prompts té problemes de mostra petita
  coneguts a la literatura.
- No modelem la dependència a nivell de sessió (un votant que vota molt).
"""

from __future__ import annotations

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from app.models import Category, Prompt, Response, Vote, Winner
from app.ranking.ranking import fit_bt


def _load_clustered_votes(
    session: Session, category_code: str
) -> tuple[dict[int, list[tuple[str, str]]], list[str]]:
    """Llegeix els vots decisius d'una categoria agrupats per prompt_id.

    Retorna:
        - mapping {prompt_id: [(guanyador, perdedor), ...]}
        - llista de models únics observats.

    Els empats i els 'neither' no entren al càlcul de confiança BT.
    """
    response_a = aliased(Response)
    response_b = aliased(Response)
    stmt = (
        select(Vote.prompt_id, Vote.winner, response_a.model, response_b.model)
        .join(Prompt, Vote.prompt_id == Prompt.id)
        .join(Category, Prompt.category_id == Category.id)
        .join(response_a, Vote.response_a_id == response_a.id)
        .join(response_b, Vote.response_b_id == response_b.id)
        .where(Category.code == category_code)
    )
    by_prompt: dict[int, list[tuple[str, str]]] = {}
    seen_models: set[str] = set()
    for prompt_id, winner, model_a, model_b in session.execute(stmt).all():
        seen_models.add(model_a)
        seen_models.add(model_b)
        if winner == Winner.a:
            by_prompt.setdefault(prompt_id, []).append((model_a, model_b))
        elif winner == Winner.b:
            by_prompt.setdefault(prompt_id, []).append((model_b, model_a))
        # els empats i els neithers no s'inclouen al bootstrap BT.
    return by_prompt, sorted(seen_models)


def _bootstrap_deltas(
    by_prompt: dict[int, list[tuple[str, str]]],
    models: list[str],
    best_model: str,
    n_bootstrap: int,
    seed: int,
    alpha: float,
) -> np.ndarray:
    """Re-mostra prompts amb reemplaçament i retorna l'array de deltas."""
    competitors = [m for m in models if m != best_model]
    prompt_ids = list(by_prompt.keys())
    n_prompts = len(prompt_ids)
    rng = np.random.default_rng(seed)

    deltas = np.empty(n_bootstrap)
    for b in range(n_bootstrap):
        sampled = rng.choice(prompt_ids, size=n_prompts, replace=True)
        votes = [v for p in sampled for v in by_prompt[p]]
        theta_b = fit_bt(votes, models, alpha=alpha)
        deltas[b] = theta_b[best_model] - max(theta_b[c] for c in competitors)
    return deltas


def assess_confidence(
    session: Session,
    category_code: str,
    n_bootstrap: int = 1000,
    alpha: float = 0.01,
    seed: int = 0,
) -> dict:
    """Avalua si tenim prou confiança per declarar un guanyador per categoria.

    Pensada per ser cridada des de `GET /api/ranking` o `GET /api/stats` a la
    microservei (tasca #6). Cost: ~5 segons (1000 ajustos BT). La microservei
    HA DE cachejar el resultat — no es pot calcular en línia a cada petició.

    Decisió: bootstrap clusteritzat amb etiquetes fixes.

    Per què clusteritzat: dos vots sobre el mateix prompt no són
    independents (comparteixen la dificultat i les peculiaritats del prompt).
    Re-mostrejar prompts sencers, no vots individuals, respecta aquesta
    dependència. Sense això, els CIs serien massa estrets ~2× (vegeu
    `docs/T7_ranking_design.md` §5 i `analysis/dimensioning.py`).

    Per què etiquetes fixes: ajustem BT una vegada sobre tot el dataset per
    identificar el "millor actual". Aquesta etiqueta queda CONGELADA. A cada
    replica del bootstrap, mesurem el gap del MATEIX model (no del millor
    d'aquella replica). Així, si el rànquing és inestable, el gap surt
    negatiu en algunes repliques — la inestabilitat es fa visible. La versió
    "sort and take rank1−rank2" era incorrecta i ho amagava (gap forçat ≥ 0).

    Mètriques retornades:
        - `p_best_is_best`: fracció de repliques bootstrap on el best fix
          encara és el millor. Útil per comunicar al públic ("guanya el 97%
          del temps quan re-mostregem").
        - `ci_lo`, `ci_hi`: percentils 2.5 i 97.5 del gap entre el best fix
          i el millor competidor. Pot ser negatiu si el rànquing és inestable.
        - `is_stable`: True si `ci_lo > 0`. Regla d'aturada operativa.

    Limitacions (cal documentar-les públicament):
        - Amb només ~10 prompts per categoria, el cluster bootstrap té
          problemes coneguts de mostra petita; els CIs són honestos però
          no màgics.
        - No modelem la dependència a nivell de sessió (un votant que vota
          molt podria distorsionar els resultats). S'abordarà a la v2 quan
          hi hagi usuaris autenticats.

    Args:
        session: sessió SQLAlchemy ja oberta.
        category_code: codi de la categoria (e.g. "correccio").
        n_bootstrap: nombre de repliques del bootstrap. 1000 sol ser prou.
        alpha: regularització L2 per a l'ajust BT (vegeu `ranking.fit_bt`).
        seed: llavor per a reproduïbilitat.

    Returns:
        Diccionari amb la forma:

        ```
        {
            "category_code": "correccio",
            "best_model": "gemma-3-4b-it",
            "n_prompts": 10,
            "n_decisive_votes": 358,
            "p_best_is_best": 0.97,    # fracció de repliques on best guanya
            "ci_lo": 0.12,             # percentil 2.5 del delta
            "ci_hi": 0.44,             # percentil 97.5 del delta
            "is_stable": True,         # True si ci_lo > 0
        }
        ```

        Si no hi ha prou vots o models per fer el bootstrap, retorna valors
        per defecte amb `is_stable=False`.
    """
    by_prompt, models = _load_clustered_votes(session, category_code)
    n_decisive = sum(len(v) for v in by_prompt.values())

    if len(models) < 2 or n_decisive == 0:
        return {
            "category_code": category_code,
            "best_model": None,
            "n_prompts": len(by_prompt),
            "n_decisive_votes": n_decisive,
            "p_best_is_best": 0.0,
            "ci_lo": 0.0,
            "ci_hi": 0.0,
            "is_stable": False,
        }

    # Pas 1: ajust complet → millor model amb etiqueta fixa.
    all_decisive = [v for vs in by_prompt.values() for v in vs]
    theta_hat = fit_bt(all_decisive, models, alpha=alpha)
    best_model = max(theta_hat, key=theta_hat.get)

    # Pas 2: bootstrap clusteritzat.
    deltas = _bootstrap_deltas(
        by_prompt=by_prompt,
        models=models,
        best_model=best_model,
        n_bootstrap=n_bootstrap,
        seed=seed,
        alpha=alpha,
    )

    ci_lo, ci_hi = np.percentile(deltas, [2.5, 97.5])
    p_best_is_best = float(np.mean(deltas > 0))

    return {
        "category_code": category_code,
        "best_model": best_model,
        "n_prompts": len(by_prompt),
        "n_decisive_votes": n_decisive,
        "p_best_is_best": round(p_best_is_best, 3),
        "ci_lo": round(float(ci_lo), 4),
        "ci_hi": round(float(ci_hi), 4),
        "is_stable": bool(ci_lo > 0),
    }
