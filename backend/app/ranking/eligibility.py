"""Recomptes i mínims d'evidència per model dins de l'àmbit consultat."""

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from app.models import Category, Prompt, Response, Vote, Winner
from app.prompt_versions import active_prompt_ids

MIN_DECISIVE_VOTES = 30
MIN_DECISIVE_PROMPTS = 10


def model_coverage(session: Session, category_code: str | None) -> list[dict]:
    """Inclou els models amb respostes actives encara que no hagin rebut vots."""
    models_query = (
        select(Response.model)
        .join(Prompt)
        .join(Category)
        .where(Prompt.id.in_(active_prompt_ids()))
        .distinct()
        .order_by(Response.model)
    )
    response_a, response_b = aliased(Response), aliased(Response)
    votes_query = (
        select(Vote.prompt_id, Vote.winner, response_a.model, response_b.model)
        .join(Prompt, Vote.prompt_id == Prompt.id)
        .join(Category)
        .join(response_a, Vote.response_a_id == response_a.id)
        .join(response_b, Vote.response_b_id == response_b.id)
        .where(Prompt.id.in_(active_prompt_ids()))
    )
    if category_code is not None:
        models_query = models_query.where(Category.code == category_code)
        votes_query = votes_query.where(Category.code == category_code)
    coverage = {
        model: {"model": model, "n_votes_total": 0, "n_votes_decisive": 0}
        for model in session.scalars(models_query)
    }
    prompts = {model: set() for model in coverage}
    for prompt_id, winner, model_a, model_b in session.execute(votes_query):
        for model in (model_a, model_b):
            coverage[model]["n_votes_total"] += 1
            if winner in (Winner.a, Winner.b):
                coverage[model]["n_votes_decisive"] += 1
                prompts[model].add(prompt_id)
    for model, item in coverage.items():
        item["n_prompts_decisive"] = len(prompts[model])
    return list(coverage.values())


def is_eligible(coverage: dict) -> bool:
    """Els dos mínims s'han de complir simultàniament."""
    return (
        coverage["n_votes_decisive"] >= MIN_DECISIVE_VOTES
        and coverage["n_prompts_decisive"] >= MIN_DECISIVE_PROMPTS
    )
