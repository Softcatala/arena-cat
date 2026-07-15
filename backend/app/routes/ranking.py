from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import RankingResponse
from app.services import ranking_service

router = APIRouter()


@router.get("/ranking")
def get_ranking(category_code: str, db: Session = Depends(get_db)) -> RankingResponse:
    """
    Retorna el rànquing per a una categoria.
    Args:
        db: Sessió de base de dades.
        category_code: Codi de la categoria.
    Returns:
        RankingResponse: objecte amb el rànquing per a la categoria.
    """
    return RankingResponse(**ranking_service.get_ranking_per_category(db, category_code))
