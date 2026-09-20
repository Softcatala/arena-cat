from fastapi import APIRouter

from app.deps import CurrentQualifiedUser, DbSession
from app.schemas import VoteRequest, VoteResponse
from app.services import vote_service

router = APIRouter()


@router.post("/vote")
def post_vote(
    vote_req: VoteRequest,
    current_user: CurrentQualifiedUser,
    db: DbSession,
) -> VoteResponse:
    """
    Envia un vot a la base de dades
    Args:
        vote_req: objecte amb el vot (winner, token)
        current_user: usuari autenticat, verificat i acreditat (injectat via dependència)
        db: sessió SQLAlchemy
    Returns:
        VoteResponse: objecte amb el status ("ok")
    """
    return vote_service.submit_vote(db, vote_req, current_user)
