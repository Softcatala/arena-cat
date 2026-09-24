from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Category, Prompt, Vote
from app.prompt_versions import active_prompt_ids
from app.ranking.confidence import assess_confidence
from app.ranking.ranking import compute_ranking


def _confidence_response(confidence: dict) -> dict:
    """Adapta les mètriques internes al contracte públic de l'API."""
    return {
        "category_code": confidence["category_code"],
        "best_model": confidence["best_model"],
        "n_prompts": confidence["n_prompts"],
        "n_decisive_votes": confidence["n_decisive_votes"],
        "p_best_is_best": confidence["p_best_is_best"],
        "confidence_interval": (
            {"lo": confidence["ci_lo"], "hi": confidence["ci_hi"]}
            if confidence["ci_lo"] is not None
            else None
        ),
        "is_stable": confidence["is_stable"],
    }


def get_ranking_per_category(db: Session, category_code: str | None) -> dict:
    """
    Obté el ranking per a una categoria o el global.
    Args:
        db: Sessió de base de dades.
        category_code: Codi opcional de la categoria.
    Returns:
        Diccionari amb el ranking demanat.
    """
    participants_query = select(func.count(Vote.user_id.distinct())).where(
        Vote.prompt_id.in_(active_prompt_ids())
    )
    if category_code is not None:
        category = db.scalar(select(Category).where(Category.code == category_code))
        if category is None:
            raise HTTPException(
                status_code=404, detail=f"No existeix la categoria: {category_code}."
            )
        participants_query = participants_query.join(Prompt, Vote.prompt_id == Prompt.id).where(
            Prompt.category_id == category.id
        )

    ranking = compute_ranking(db, category_code)
    ranking["n_participants"] = db.scalar(participants_query)
    ranking["confidence"] = _confidence_response(assess_confidence(db, category_code))
    if ranking["confidence"]["confidence_interval"] is None:
        ranking["status"] = "insufficient_data"
    elif ranking["confidence"]["is_stable"]:
        ranking["status"] = "stable"
    else:
        ranking["status"] = "provisional"
    return ranking
