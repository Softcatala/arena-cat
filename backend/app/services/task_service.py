from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Category, TaskSkip, User
from app.ranking.sampler import select_next_task
from app.schemas import SkipTaskRequest, SkipTaskResponse, TaskResponse
from app.security import create_task_token, verify_task_token


def get_next_task_for_user(category_code: str | None, user: User, db: Session) -> TaskResponse:
    """Retorna la propera tasca per a un usuari

    Args:
        db: sessió SQLAlchemy
        category_code: codi opcional de la categoria (e.g. "correccio", "reformulacio")
        user: usuari autenticat i verificat

    Returns:
        TaskResponse: objecte amb el prompt, les dues respostes i el token
    """
    # Obtenim la propera tasca via el mòdul ranking
    if category_code is not None:
        task = select_next_task(db, category_code, user.id)
    else:
        task = None
        for code in db.scalars(select(Category.code).order_by(Category.code)):
            task = select_next_task(db, code, user.id)
            if task is not None:
                break

    # Retornem excepció en cas de que no quedin tasques disponibles
    if task is None:
        raise HTTPException(
            status_code=404, detail="No hi ha tasques disponibles o bé les has realitzat totes."
        )

    # En cas que hi hagi tasca, s'extreuen els identificadors
    prompt_id = task["prompt_id"]
    response_a_id = task["response_a_id"]
    response_b_id = task["response_b_id"]

    # Creem el token amb els identificadors
    token = create_task_token(prompt_id, response_a_id, response_b_id, user.id)

    # Retornem la tasca i el token
    return TaskResponse(
        category_code=task["category_code"],
        prompt=task["prompt_text"],
        response_a=task["response_a_text"],
        response_b=task["response_b_text"],
        token=token,
    )


def skip_task_for_user(skip_req: SkipTaskRequest, user: User, db: Session) -> SkipTaskResponse:
    """Desa que un usuari ha omès una tasca."""
    payload = verify_task_token(skip_req.token)
    if not payload:
        raise HTTPException(status_code=401, detail="El token és invàlid o ha caducat")

    if int(payload.get("user_id", -1)) != user.id:
        raise HTTPException(status_code=403, detail="El token no correspon a l'usuari autenticat")

    skip = TaskSkip(
        prompt_id=payload["prompt_id"],
        user_id=user.id,
        response_a_id=payload["response_a_id"],
        response_b_id=payload["response_b_id"],
    )

    db.add(skip)
    try:
        db.commit()
    except IntegrityError as err:
        db.rollback()
        if "uq_task_skips_user_prompt_pair" not in str(err.orig):
            raise HTTPException(
                status_code=400, detail="L'omissió no s'ha pogut processar"
            ) from err

    return SkipTaskResponse(status="ok")
