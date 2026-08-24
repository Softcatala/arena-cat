from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import RankingResponse
from app.services import ranking_service

router = APIRouter()


@router.get("/ranking")
def get_ranking(category_code: str | None = None, db: Session = Depends(get_db)) -> RankingResponse:
    """
    Retorna el rànquing per a una categoria o el rànquing global.
    Args:
        db: Sessió de base de dades.
        category_code: Codi opcional de la categoria. Si no s'informa, retorna el rànquing global.
    Returns:
        RankingResponse: objecte amb el rànquing demanat.
    """
    return RankingResponse(**ranking_service.get_ranking_per_category(db, category_code))
