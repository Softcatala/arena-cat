from collections import defaultdict
from itertools import combinations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import TaskTokenError
from app.models import Category, Response, TaskSkip, User, Vote
from app.ranking.sampler import select_next_task
from app.schemas import SkipTaskRequest, SkipTaskResponse, TaskProgressResponse, TaskResponse
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
        raise TaskTokenError(detail="El token és invàlid o ha caducat")

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


def _cells(rows) -> set[tuple[int, int, int]]:
    return {
        (prompt_id, min(response_a_id, response_b_id), max(response_a_id, response_b_id))
        for prompt_id, response_a_id, response_b_id in rows
    }


def get_task_progress_for_user(user: User, db: Session) -> TaskProgressResponse:
    """Retorna el progrés global de tasques d'un usuari."""
    responses_by_prompt = defaultdict(list)
    for prompt_id, response_id in db.execute(select(Response.prompt_id, Response.id)).all():
        responses_by_prompt[prompt_id].append(response_id)

    total_cells = {
        (prompt_id, response_a_id, response_b_id)
        for prompt_id, response_ids in responses_by_prompt.items()
        for response_a_id, response_b_id in combinations(sorted(response_ids), 2)
    }
    voted_cells = _cells(
        db.execute(
            select(Vote.prompt_id, Vote.response_a_id, Vote.response_b_id).where(
                Vote.user_id == user.id
            )
        ).all()
    )
    skipped_cells = _cells(
        db.execute(
            select(TaskSkip.prompt_id, TaskSkip.response_a_id, TaskSkip.response_b_id).where(
                TaskSkip.user_id == user.id
            )
        ).all()
    )
    done_cells = voted_cells | skipped_cells

    return TaskProgressResponse(
        total=len(total_cells),
        voted=len(voted_cells),
        skipped=len(skipped_cells),
        remaining=len(total_cells - done_cells),
    )
