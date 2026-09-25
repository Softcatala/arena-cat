from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import TaskTokenError
from app.models import User, Vote, Winner
from app.prompt_versions import require_active_prompt
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
        raise TaskTokenError(detail="El token és invàlid o ha caducat")

    if int(payload.get("user_id", -1)) != user.id:
        raise HTTPException(status_code=403, detail="El token no correspon a l'usuari autenticat")

    if datetime.now(UTC).timestamp() < payload["vote_after"]:
        raise HTTPException(status_code=425, detail="Espera almenys 10 segons abans de votar")

    prompt_id = payload["prompt_id"]
    response_a_id = payload["response_a_id"]
    response_b_id = payload["response_b_id"]

    require_active_prompt(db, prompt_id)
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
        # L'índex únic evita duplicats, també si dos reintents arriben alhora.
        if "uq_votes_user_prompt_pair" in str(err.orig):
            existing = db.scalar(
                select(Vote).where(
                    Vote.user_id == user.id,
                    Vote.prompt_id == prompt_id,
                    func.least(Vote.response_a_id, Vote.response_b_id)
                    == min(response_a_id, response_b_id),
                    func.greatest(Vote.response_a_id, Vote.response_b_id)
                    == max(response_a_id, response_b_id),
                )
            )
            if existing is not None:
                expected_winner = vote_req.winner
                if existing.response_a_id != response_a_id:
                    expected_winner = {Winner.a: Winner.b, Winner.b: Winner.a}.get(
                        expected_winner, expected_winner
                    )
                if existing.winner == expected_winner:
                    return VoteResponse(status="ok")
            raise HTTPException(
                status_code=409, detail="Ja heu votat aquesta parella de respostes"
            ) from err
        raise HTTPException(status_code=400, detail="El vot no s'ha pogut processar") from err

    return VoteResponse(status="ok")
