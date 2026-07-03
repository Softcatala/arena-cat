"""Tria la propera tasca a mostrar a un avaluador.

`select_next_task` retorna un diccionari amb el prompt, les dues respostes
i la informació necessària perquè la microservei la mostri a l'usuari.

Estratègia per defecte: **quota-balanced randomization**.

- Considera cada combinació (prompt, parella ordenada de models) com una
  cel·la.
- Tria uniformement entre les cel·les que actualment tenen menys vots.
- Randomitza l'ordre A/B per evitar biaix de posició.
- Si es passa `session_id`, exclou les cel·les en les quals aquesta sessió
  ja ha votat per evitar repeticions.

Aquesta estratègia és preferible a la iid uniform (que genera variància
Poisson entre cel·les) i no pateix crítica de "Leaderboard Illusion"
(els pesos no depenen de cap rànquing acumulat).

Vegeu `docs/T7_ranking_design.md` §4 per a la motivació completa.
"""

from __future__ import annotations

from collections import Counter
from itertools import combinations

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from app.models import Category, Prompt, Response, Vote


def _load_prompts_and_responses(
    session: Session, category_code: str
) -> list[tuple[Prompt, dict[str, Response]]]:
    """Llegeix els prompts de la categoria amb totes les seves respostes.

    Retorna una llista de tuples (prompt, {model: response}).
    """
    stmt = (
        select(Prompt)
        .join(Category, Prompt.category_id == Category.id)
        .where(Category.code == category_code)
    )
    prompts = session.scalars(stmt).all()
    out = []
    for prompt in prompts:
        responses_by_model = {r.model: r for r in prompt.responses}
        if len(responses_by_model) >= 2:
            out.append((prompt, responses_by_model))
    return out


def _existing_vote_counts(session: Session, prompt_ids: list[int]) -> Counter:
    """Compta vots existents per (prompt_id, model_a, model_b) en parella ordenada."""
    if not prompt_ids:
        return Counter()
    # Llegim els vots i fem el join amb responses per obtenir els models.
    response_a = aliased(Response)
    response_b = aliased(Response)
    stmt = (
        select(Vote.prompt_id, response_a.model, response_b.model)
        .join(response_a, Vote.response_a_id == response_a.id)
        .join(response_b, Vote.response_b_id == response_b.id)
        .where(Vote.prompt_id.in_(prompt_ids))
    )
    counts: Counter = Counter()
    for prompt_id, model_a, model_b in session.execute(stmt).all():
        key = (prompt_id, *sorted((model_a, model_b)))
        counts[key] += 1
    return counts


def _cells_voted_by_session(
    session: Session, prompt_ids: list[int], session_id: str
) -> set[tuple[int, str, str]]:
    """Retorna les cel·les (prompt_id, model_a, model_b) on `session_id` ja ha votat.

    Servirà per excloure-les del proper sampling i no demanar el mateix dues
    vegades a la mateixa persona.
    """
    if not prompt_ids:
        return set()
    response_a = aliased(Response)
    response_b = aliased(Response)
    stmt = (
        select(Vote.prompt_id, response_a.model, response_b.model)
        .join(response_a, Vote.response_a_id == response_a.id)
        .join(response_b, Vote.response_b_id == response_b.id)
        .where(Vote.prompt_id.in_(prompt_ids))
        .where(Vote.session_id == session_id)
    )
    voted: set[tuple[int, str, str]] = set()
    for prompt_id, model_a, model_b in session.execute(stmt).all():
        voted.add((prompt_id, *sorted((model_a, model_b))))
    return voted


def select_next_task(
    session: Session,
    category_code: str,
    session_id: str | None = None,
    seed: int | None = None,
) -> dict | None:
    """Tria la propera tasca a mostrar a un avaluador.

    Pensada per ser cridada des de `GET /api/task` a la microservei (tasca #6).
    Cada crida és independent: només llegeix recomptes de vots a la base de
    dades; no ajusta cap model i no manté estat. Cost: ~10 ms.

    Decisió: estratègia **quota-balanced randomization**.

        - Una cel·la és un trio (prompt, parella ordenada de models).
        - A cada crida, busca les cel·les que actualment empaten al recompte
          mínim de vots i en tria una uniformement a l'atzar.
        - Quan totes les cel·les igualen recompte, esdevé aleatori uniforme.
        - Randomitza l'ordre A/B per evitar biaix de posició.

    Si es passa `session_id`, exclou les cel·les on aquesta sessió ja ha
    votat: una mateixa persona no veurà dos cops la mateixa (prompt, parella).
    Quan una sessió ja ha votat a TOTES les cel·les de la categoria, retorna
    None — la microservei interpretarà això com "aquest avaluador ja ha
    completat aquesta categoria, mostra-li una altra cosa o agraeix-li la
    contribució".

    Per què NO iid uniforme: amb un pressupost petit (133 vots/cel·la a la
    Fita 1), iid genera variància Poisson que deixa cel·les amb el doble de
    vots que altres. La validació empírica a `analysis/phase1/04_samplers_comparison.py`
    mostra que quota-balanced arriba a un rànquing estable amb ~2.5× menys
    vots. Vegeu `docs/T7_ranking_design.md` §4 per la motivació completa.

    Per què NO depèn del rànquing actual: això la fa robusta a la crítica
    "Leaderboard Illusion" (Singh et al. 2025) — no hi ha bucle entre vots
    acumulats i futur sampling.

    Args:
        session: sessió SQLAlchemy ja oberta.
        category_code: codi de la categoria (e.g. "correccio", "reformulacio").
        session_id: identificador anònim de la sessió de l'usuari. Si es
            proporciona, exclou les cel·les en les quals aquesta sessió ja
            ha votat. Si és None, no es filtra per sessió.
        seed: opcional, per reproduïbilitat als tests.

    Returns:
        Diccionari amb la forma:

        ```
        {
            "category_code": "correccio",
            "prompt_id": 42,
            "prompt_text": "Corregeix aquest text...",
            "response_a_id": 100,
            "response_a_text": "...",
            "response_b_id": 101,
            "response_b_text": "...",
        }
        ```

        Retorna None en dos casos:
            - La categoria no té cap prompt amb almenys dues respostes.
            - `session_id` ha votat a totes les cel·les disponibles.

        Els identificadors de model (`model_a`, `model_b`) NO es retornen:
        l'avaluació és cega. La microservei pot recuperar-los des de Response
        si li cal registrar el mapping al gravar el vot.
    """
    rng = np.random.default_rng(seed)
    prompts_with_responses = _load_prompts_and_responses(session, category_code)
    if not prompts_with_responses:
        return None

    # Construïm totes les cel·les possibles: (prompt_id, parella ordenada de models).
    cells: list[tuple[int, str, str]] = []
    cell_to_responses: dict[tuple[int, str, str], tuple[Prompt, Response, Response]] = {}
    for prompt, responses in prompts_with_responses:
        models = sorted(responses.keys())
        for model_a, model_b in combinations(models, 2):
            cell = (prompt.id, model_a, model_b)
            cells.append(cell)
            cell_to_responses[cell] = (prompt, responses[model_a], responses[model_b])

    if not cells:
        return None

    prompt_ids = [p.id for p, _ in prompts_with_responses]

    # Si tenim session_id, excloem les cel·les que aquesta sessió ja ha votat.
    # Si la sessió ja ha votat a totes les cel·les, retornem None per indicar
    # que aquest avaluador ja ha completat la categoria.
    if session_id is not None:
        already_voted = _cells_voted_by_session(session, prompt_ids, session_id)
        cells = [c for c in cells if c not in already_voted]
        if not cells:
            return None

    # Busquem el recompte mínim de vots i recollim TOTES les cel·les empatades a aquell mínim.
    # Després triem una uniformement a l'atzar: la combinació "empatats al mínim + atzar"
    # és la que evita biaixos d'ordre i fa convergir els recomptes a valors igualats.
    counts = _existing_vote_counts(session, prompt_ids)
    min_count = min(counts.get(c, 0) for c in cells)
    underfilled = [c for c in cells if counts.get(c, 0) == min_count]
    chosen = underfilled[int(rng.integers(len(underfilled)))]
    prompt, response_a, response_b = cell_to_responses[chosen]

    # Randomitzem l'ordre A/B per evitar biaix de posició.
    if rng.random() < 0.5:
        response_a, response_b = response_b, response_a

    return {
        "category_code": category_code,
        "prompt_id": prompt.id,
        "prompt_text": prompt.text,
        "response_a_id": response_a.id,
        "response_a_text": response_a.text,
        "response_b_id": response_b.id,
        "response_b_text": response_b.text,
    }
