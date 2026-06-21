"""Infraestructura de SQLAlchemy: classe base declarativa i fàbriques de motor i sessions.

El motor fa servir el rol d'aplicació amb permisos limitats (database_url) i només
es crea quan algú demana get_engine().
"""

from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Classe base de tots els models declaratius."""


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, future=True, pool_pre_ping=True)


@lru_cache
def get_sessionmaker() -> sessionmaker:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)
