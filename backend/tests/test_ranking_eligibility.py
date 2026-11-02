"""Comprova els mínims d'evidència del rànquing públic."""

import pytest

from app.models import Prompt, Response, Winner
from tests.test_ranking import MODELS, _record_vote, _seed_prompts


@pytest.mark.parametrize(
    ("n_votes", "n_prompts", "eligible"),
    [(0, 10, False), (29, 10, False), (30, 9, False), (30, 10, True)],
)
def test_public_ranking_requires_both_thresholds(client, session, n_votes, n_prompts, eligible):
    prompts = _seed_prompts(session, "correccio", n_prompts)
    for i in range(n_votes):
        prompt, responses = prompts[i % n_prompts]
        _record_vote(session, prompt, responses[MODELS[0]], responses[MODELS[1]], Winner.a)
    session.flush()
    data = client.get("/api/ranking", params={"category_code": "correccio"}).json()
    assert [item["model"] for item in data["ranked_models"]] == (MODELS[:2] if eligible else [])
    assert data["best_model"] == (MODELS[0] if eligible else None)
    assert data["n_votes_total"] == n_votes
    if not eligible:
        assert data["status"] == "insufficient_data"
        assert data["confidence"]["best_model"] is None
        assert data["confidence"]["is_stable"] is False


def test_new_winning_model_cannot_displace_eligible_leader(client, session):
    prompts = _seed_prompts(session, "correccio", 10)
    for prompt, responses in prompts:
        for _ in range(3):
            _record_vote(session, prompt, responses[MODELS[0]], responses[MODELS[1]], Winner.a)
    prompt, responses = prompts[0]
    _record_vote(session, prompt, responses[MODELS[2]], responses[MODELS[0]], Winner.a)
    for winner in (Winner.tie, Winner.neither):
        for _ in range(30):
            _record_vote(session, prompt, responses[MODELS[2]], responses[MODELS[1]], winner)
    session.flush()
    data = client.get("/api/ranking").json()
    assert data["best_model"] == data["confidence"]["best_model"] == MODELS[0]
    assert {item["model"] for item in data["ranked_models"]} == set(MODELS[:2])
    assert data["n_votes_total"] == 91


def test_eligibility_is_scoped_to_category_and_active_versions(client, session):
    for category in ("correccio", "traduccio"):
        for prompt, responses in _seed_prompts(session, category, 5):
            for _ in range(3):
                _record_vote(session, prompt, responses[MODELS[0]], responses[MODELS[1]], Winner.a)
    session.flush()
    assert len(client.get("/api/ranking").json()["ranked_models"]) == 2
    data = client.get("/api/ranking", params={"category_code": "correccio"}).json()
    assert data["ranked_models"] == []
    old, old_responses = _seed_prompts(session, "generacio", 1)[0]
    for _ in range(30):
        _record_vote(session, old, old_responses[MODELS[0]], old_responses[MODELS[1]], Winner.a)
    session.flush()
    new = Prompt(code=old.code, version="v2", category_id=old.category_id, text="Nou")
    session.add(new)
    session.flush()
    for model in MODELS[:2]:
        session.add(Response(prompt_id=new.id, model=model, text="Nova resposta"))
    session.flush()
    data = client.get("/api/ranking", params={"category_code": "generacio"}).json()
    assert data["ranked_models"] == []
    assert data["n_votes_total"] == 0


def test_model_is_promoted_when_last_required_vote_arrives(client, session):
    prompts = _seed_prompts(session, "correccio", 10)
    for i in range(29):
        prompt, responses = prompts[i % 10]
        _record_vote(session, prompt, responses[MODELS[0]], responses[MODELS[1]], Winner.b)
    session.flush()
    assert client.get("/api/ranking").json()["ranked_models"] == []
    prompt, responses = prompts[-1]
    _record_vote(session, prompt, responses[MODELS[0]], responses[MODELS[1]], Winner.b)
    session.flush()
    data = client.get("/api/ranking").json()
    assert data["best_model"] == MODELS[1]
    assert len(data["ranked_models"]) == 2
    assert data["ranked_models"][1]["model"] == MODELS[0]
    assert data["confidence"]["best_model"] == MODELS[1]
