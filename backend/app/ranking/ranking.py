"""Calcula el rànquing dels models per categoria.

La funció  `compute_ranking` retorna:

- el millor model segons Bradley-Terry,
- els skills BT (sumats a zero per identificabilitat),
- la matriu bruta de win-rates per parella,
- recomptes globals (vots decisius, empats, neithers),
- detecció de cicles a la matriu bruta (per a n=3 és possible: A>B>C>A).

Convencions:
- Només els vots decisius (winner='a' o 'b') entren a l'ajust BT.
- Els empats i els "neither" es reporten per separat per a transparència.
- Skills sumats a zero; regularització L2 amb `alpha=0.01` per evitar
  divergències en cas de separació completa.
"""

from __future__ import annotations

from itertools import combinations

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, log_expit
from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from app.models import Category, Prompt, Response, Vote, Winner

# ---------------------------------------------------------------------------
# Ajustador BT — el mateix que vam validar a `analysis/phase1/02_bt_fitter.py`.
# ---------------------------------------------------------------------------


def _negative_log_likelihood(
    theta: np.ndarray,
    winner_idx: np.ndarray,
    loser_idx: np.ndarray,
    alpha: float,
) -> float:
    """NLL regularitzada per a BT vectoritzada."""
    diffs = theta[winner_idx] - theta[loser_idx]
    log_likelihood = log_expit(diffs).sum()
    penalty = alpha * (theta**2).sum()
    return -log_likelihood + penalty


def _gradient(
    theta: np.ndarray,
    winner_idx: np.ndarray,
    loser_idx: np.ndarray,
    alpha: float,
) -> np.ndarray:
    """Gradient analític de la NLL respecte a theta."""
    diffs = theta[winner_idx] - theta[loser_idx]
    residuals = 1.0 - expit(diffs)
    grad = np.zeros_like(theta)
    np.add.at(grad, winner_idx, -residuals)
    np.add.at(grad, loser_idx, residuals)
    grad += 2.0 * alpha * theta
    return grad


def fit_bt(
    decisive_votes: list[tuple[str, str]],
    models: list[str],
    alpha: float = 0.01,
) -> dict[str, float]:
    """Ajusta Bradley-Terry per màxima versemblança amb sum-to-zero.

    Args:
        decisive_votes: llista de tuples (guanyador, perdedor) per a cada vot decisiu.
        models: identificadors dels models, en ordre estable.
        alpha: pes de la regularització L2.

    Returns:
        Diccionari {model: skill BT}. Els skills sumen zero.
    """
    if not decisive_votes:
        return {m: 0.0 for m in models}
    model_to_idx = {m: i for i, m in enumerate(models)}
    winner_idx = np.array([model_to_idx[w] for w, _ in decisive_votes])
    loser_idx = np.array([model_to_idx[loser] for _, loser in decisive_votes])
    theta0 = np.zeros(len(models))
    result = minimize(
        _negative_log_likelihood,
        theta0,
        args=(winner_idx, loser_idx, alpha),
        jac=_gradient,
        method="L-BFGS-B",
    )
    theta = result.x - result.x.mean()
    return dict(zip(models, theta, strict=True))


# ---------------------------------------------------------------------------
# Càrrega de vots d'una categoria + càlcul de la matriu
# ---------------------------------------------------------------------------


def _load_votes_for_category(session: Session, category_code: str) -> list[tuple[Winner, str, str]]:
    """Llegeix els vots d'una categoria com a tuples (winner, model_a, model_b).

    Fem JOIN doble amb la taula responses per obtenir els identificadors de
    model (no els IDs de resposta), perquè el rànquing opera per model.
    """
    response_a = aliased(Response)
    response_b = aliased(Response)
    stmt = (
        select(Vote.winner, response_a.model, response_b.model)
        .join(Prompt, Vote.prompt_id == Prompt.id)
        .join(Category, Prompt.category_id == Category.id)
        .join(response_a, Vote.response_a_id == response_a.id)
        .join(response_b, Vote.response_b_id == response_b.id)
        .where(Category.code == category_code)
    )
    return list(session.execute(stmt).all())


def _pairwise_stats(
    raw: list[tuple[Winner, str, str]],
    models: list[str],
) -> list[dict]:
    """Comptes per parella ordenada (a, b) amb a < b alfabèticament."""
    pairs = [tuple(sorted(p)) for p in combinations(models, 2)]
    counts = {p: {"wins_a": 0, "wins_b": 0, "ties": 0, "neither": 0} for p in pairs}
    for winner, model_a, model_b in raw:
        key = tuple(sorted((model_a, model_b)))
        if key not in counts:
            continue  # parella amb un model no esperat: ignora
        if winner == Winner.tie:
            counts[key]["ties"] += 1
        elif winner == Winner.neither:
            counts[key]["neither"] += 1
        elif (winner == Winner.a and model_a == key[0]) or (
            winner == Winner.b and model_b == key[0]
        ):
            counts[key]["wins_a"] += 1
        else:
            counts[key]["wins_b"] += 1

    stats = []
    for (a, b), c in counts.items():
        decisive = c["wins_a"] + c["wins_b"]
        win_rate_a = c["wins_a"] / decisive if decisive > 0 else None
        stats.append(
            {
                "model_a": a,
                "model_b": b,
                "wins_a": c["wins_a"],
                "wins_b": c["wins_b"],
                "ties": c["ties"],
                "neither": c["neither"],
                "win_rate_a": win_rate_a,
            }
        )
    return stats


def _detect_cycle_3way(stats: list[dict]) -> tuple[bool, list[str]]:
    """Detecta un cicle A>B>C>A a partir de les taxes brutes (només per n=3)."""
    if len(stats) != 3:
        return False, []
    # Direcció: el guanyador de cada parella és qui té win_rate_a > 0.5
    # (o model_b si win_rate_a < 0.5).
    edges: dict[str, str] = {}
    for s in stats:
        if s["win_rate_a"] is None:
            return False, []
        winner = s["model_a"] if s["win_rate_a"] > 0.5 else s["model_b"]
        loser = s["model_b"] if s["win_rate_a"] > 0.5 else s["model_a"]
        edges[winner] = loser

    if len(edges) != 3:
        return False, []
    # Cicle: cada model apunta a un altre i tots tornen al punt de partida.
    start = next(iter(edges))
    path = [start]
    for _ in range(3):
        path.append(edges[path[-1]])
    return path[0] == path[-1], path


def _models_for_category(
    raw: list[tuple[Winner, str, str]],
) -> list[str]:
    """Extreu la llista única de models que apareixen als vots."""
    seen = set()
    for _, model_a, model_b in raw:
        seen.add(model_a)
        seen.add(model_b)
    return sorted(seen)


def compute_ranking(session: Session, category_code: str) -> dict:
    """Calcula el rànquing actual d'una categoria.

    Pensada per ser cridada des de `GET /api/ranking` a la microservei
    (tasca #6). Cost: ~30 ms (un sol ajust BT sobre tots els vots de la
    categoria). La microservei pot cachejar el resultat uns minuts.

    No hi ha estat persistit: cada crida recalcula des de zero llegint
    TOTS els vots de la base de dades. Això és intencional — qualsevol vot
    afegit a `votes` es reflecteix al següent rànquing sense pas de sync.

    Decisions clau:
        - **BT per categoria**, no global. La pregunta del producte és
          "quin model és millor a correcció / cultura / traducció", no un
          rànquing únic.
        - **Taxes brutes + BT**, no només BT. Per a n=3 models, el guany
          de BT sobre la taxa bruta és modest (~30%); reportem totes dues
          per transparència pública.
        - **Empats i 'neither' es reporten per separat, mai entren a BT.**
          Tie = "tots dos comparables"; neither = "tots dos fallits";
          són senyals diferents, no equivalents.
        - **Skills sumats a zero** per identificabilitat (BT és invariant
          a desplaçaments). Només els *gaps* són significatius.
        - **Detecció de cicles** A>B>C>A a les taxes brutes: per a n=3
          és possible i informatiu (heterogeneïtat real entre prompts),
          no un bug. BT el suavitzaria; nosaltres el reportem.

    Args:
        session: sessió SQLAlchemy ja oberta.
        category_code: codi de la categoria (e.g. "correccio").

    Returns:
        Diccionari amb la forma:

        ```
        {
            "category_code": "correccio",
            "n_votes_total": 390,
            "n_votes_decisive": 358,
            "n_ties": 23,
            "n_neither": 9,
            "models": ["gemma-3-4b-it", "qwen-3.5-9b", "salamandra-7b-instruct"],
            "best_model": "gemma-3-4b-it",
            "bt_skills": {"gemma-3-4b-it": 0.27, "qwen-3.5-9b": -0.04, ...},
            "raw_pairwise": [
                {"model_a": ..., "model_b": ..., "wins_a": ..., ...},
            ],
            "cycle_detected": False,
            "cycle_path": [],
        }
        ```

        Si no hi ha vots a la categoria, `best_model` és None i `bt_skills`
        és buit.
    """
    raw = _load_votes_for_category(session, category_code)
    if not raw:
        return {
            "category_code": category_code,
            "n_votes_total": 0,
            "n_votes_decisive": 0,
            "n_ties": 0,
            "n_neither": 0,
            "models": [],
            "best_model": None,
            "bt_skills": {},
            "raw_pairwise": [],
            "cycle_detected": False,
            "cycle_path": [],
        }

    models = _models_for_category(raw)
    n_total = len(raw)
    n_ties = sum(1 for w, _, _ in raw if w == Winner.tie)
    n_neither = sum(1 for w, _, _ in raw if w == Winner.neither)
    n_decisive = n_total - n_ties - n_neither

    # Per BT només els vots decisius.
    decisive: list[tuple[str, str]] = []
    for winner, model_a, model_b in raw:
        if winner == Winner.a:
            decisive.append((model_a, model_b))
        elif winner == Winner.b:
            decisive.append((model_b, model_a))

    bt_skills = fit_bt(decisive, models, alpha=0.01)
    best_model = max(bt_skills, key=bt_skills.get) if bt_skills else None

    raw_pairwise = _pairwise_stats(raw, models)
    cycle, cycle_path = _detect_cycle_3way(raw_pairwise)

    return {
        "category_code": category_code,
        "n_votes_total": n_total,
        "n_votes_decisive": n_decisive,
        "n_ties": n_ties,
        "n_neither": n_neither,
        "models": models,
        "best_model": best_model,
        "bt_skills": {m: round(s, 4) for m, s in bt_skills.items()},
        "raw_pairwise": raw_pairwise,
        "cycle_detected": cycle,
        "cycle_path": cycle_path if cycle else [],
    }
