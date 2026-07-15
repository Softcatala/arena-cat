from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_verified_user
from app.models import User
from app.schemas import TaskResponse
from app.services import task_service

router = APIRouter()


@router.get("/task")
def get_task(
    category_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> TaskResponse:
    """
    Retorna la propera tasca per a un usuari utilitzant el servei task_service
    Args:
        db: sessió SQLAlchemy
        category_code: codi de la categoria (e.g. "correccio", "reformulacio")
        current_user: usuari autenticat i verificat
    Returns:
        TaskResponse: objecte amb el prompt, les dues respostes i el token
    """
    return task_service.get_next_task_for_user(category_code, current_user, db)
