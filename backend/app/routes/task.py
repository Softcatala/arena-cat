from fastapi import APIRouter

from app.deps import CurrentVerifiedUser, DbSession
from app.schemas import TaskResponse
from app.services import task_service

router = APIRouter()


@router.get("/task")
def get_task(
    current_user: CurrentVerifiedUser,
    db: DbSession,
    category_code: str | None = None,
) -> TaskResponse:
    """
    Retorna la propera tasca per a un usuari utilitzant el servei task_service
    Args:
        category_code: codi opcional de la categoria (e.g. "correccio", "reformulacio")
        current_user: usuari autenticat i verificat (injectat via dependència)
        db: sessió SQLAlchemy
    Returns:
        TaskResponse: objecte amb el prompt, les dues respostes i el token
    """
    return task_service.get_next_task_for_user(category_code, current_user, db)
