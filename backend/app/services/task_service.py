from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.ranking.sampler import select_next_task
from app.schemas import TaskResponse
from app.security import create_task_token


def get_next_task_for_user(category_code: str, session_id: str, db: Session) -> TaskResponse:
    """Retorna la propera tasca per a un usuari

    Args:
        db: sessió SQLAlchemy
        category_code: codi de la categoria (e.g. "correccio", "reformulacio")
        session_id: identificador de la sessió

    Returns:
        TaskResponse: objecte amb el prompt, les dues respostes i el token
    """
    # Obtenim la propera tasca via el mòdul ranking
    task = select_next_task(db, category_code, session_id)

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
    token = create_task_token(prompt_id, response_a_id, response_b_id, session_id)

    # Retornem la tasca i el token
    return TaskResponse(
        prompt=task["prompt_text"],
        response_a=task["response_a_text"],
        response_b=task["response_b_text"],
        token=token,
    )
