from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Vote
from app.schemas import VoteRequest, VoteResponse
from app.security import verify_token


def submit_vote(db: Session, vote_req: VoteRequest):
    """"""
    payload = verify_token(vote_req.token)
    if not payload:
        raise HTTPException(status_code=401, detail="El token és invàlid o ha caducat")

    prompt_id = payload["prompt_id"]
    response_a_id = payload["response_a_id"]
    response_b_id = payload["response_b_id"]
    session_id = payload["session_id"]

    vote = Vote(
        prompt_id=prompt_id,
        response_a_id=response_a_id,
        response_b_id=response_b_id,
        winner=vote_req.winner,
        session_id=session_id,
    )

    db.add(vote)
    try:
        db.commit()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(status_code=400, detail="El vot no s'ha pogut processar") from err

    return VoteResponse(status="ok")
