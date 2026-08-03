from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category, User
from app.ranking.sampler import select_next_task
from app.schemas import TaskResponse
from app.security import create_task_token


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
