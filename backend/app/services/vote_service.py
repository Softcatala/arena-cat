from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User, Vote
from app.schemas import VoteRequest, VoteResponse
from app.security import verify_task_token


def submit_vote(db: Session, vote_req: VoteRequest, user: User):
    """Registra el vot d'un usuari a partir d'un token de tasca vàlid.

    Verifica el token, comprova que correspon a l'usuari autenticat i desa el vot.

    Args:
        db: sessió SQLAlchemy.
        vote_req: cos de la petició amb el guanyador i el token de la tasca.
        user: usuari autenticat i verificat que emet el vot.

    Returns:
        VoteResponse: objecte amb l'estat ("ok").
    """
    payload = verify_task_token(vote_req.token)
    if not payload:
        raise HTTPException(status_code=401, detail="El token és invàlid o ha caducat")

    if int(payload.get("user_id", -1)) != user.id:
        raise HTTPException(status_code=403, detail="El token no correspon a l'usuari autenticat")

    prompt_id = payload["prompt_id"]
    response_a_id = payload["response_a_id"]
    response_b_id = payload["response_b_id"]

    vote = Vote(
        prompt_id=prompt_id,
        user_id=user.id,
        response_a_id=response_a_id,
        response_b_id=response_b_id,
        winner=vote_req.winner,
    )

    db.add(vote)
    try:
        db.commit()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(status_code=400, detail="El vot no s'ha pogut processar") from err

    return VoteResponse(status="ok")
