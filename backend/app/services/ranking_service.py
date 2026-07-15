from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.ranking.ranking import compute_ranking
from app.models import Category

def get_ranking_per_category(db: Session, category_code: str) -> dict:
    """
    Obté el ranking per a una categoria.
    Args:
        db: Sessió de base de dades.
        category_code: Codi de la categoria.
    Returns:
        Diccionari amb el ranking per a la categoria.
    """
    category = db.scalar(select(Category).where(Category.code == category_code))
    if category is None:
        raise HTTPException(status_code=404, detail=f"No existeix la categoria: {category_code}.")
    return compute_ranking(db, category_code)