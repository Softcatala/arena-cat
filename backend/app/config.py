"""Configuració de l'aplicació, llegida de variables d'entorn o del fitxer .env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# El .env viu a l'arrel del repositori (un nivell per sobre de backend/).
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Paràmetres de connexió a la base de dades.

    - database_url: rol d'aplicació amb permisos limitats (opcional; la consumeix el servei).
    - database_admin_url: superusuari, per a les migracions d'Alembic.
    - database_test_url: base de dades aïllada per als tests.
    """

    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    database_url: str | None = None
    database_admin_url: str
    database_test_url: str


@lru_cache
def get_settings() -> Settings:
    return Settings()
