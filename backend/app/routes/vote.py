from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import VoteRequest, VoteResponse
from app.services import vote_service

router = APIRouter()


@router.post("/vote")
def post_vote(vote_req: VoteRequest, db: Session = Depends(get_db)) -> VoteResponse:
    """
    Envia un vot a la base de dades
    Args:
        db: sessió SQLAlchemy
        vote_req: objecte amb el vot (prompt_id, response_a_id, response_b_id, winner, session_id)
    Returns:
        VoteResponse: objecte amb el status ("ok")
    """
    return vote_service.submit_vote(db, vote_req)
