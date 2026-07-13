"""Configuració de l'aplicació, llegida de variables d'entorn o del fitxer .env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

# El .env viu a l'arrel del repositori (un nivell per sobre de backend/).
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Components de connexió a PostgreSQL. Les URLs es componen a partir d'aquí."""

    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    db_host: str = "localhost"
    postgres_port: int = 5432
    # Superusuari: migracions i tests.
    postgres_user: str
    postgres_password: str
    postgres_db: str
    # Rol d'aplicació amb permisos limitats: el consumeix el servei.
    app_db_user: str
    app_db_password: str
    # HMAC Secret Key
    hmac_secret_key: str
    # Pepper per derivar email_hash i detectar re-registres.
    email_hash_pepper: str
    # Versió de consentiment acceptada al registre.
    consent_version: str = "v1"

    def _url(self, user: str, password: str, database: str) -> str:
        return URL.create(
            "postgresql+psycopg",
            username=user,
            password=password,
            host=self.db_host,
            port=self.postgres_port,
            database=database,
        ).render_as_string(hide_password=False)

    @property
    def database_admin_url(self) -> str:
        """Superusuari, per a les migracions d'Alembic."""
        return self._url(self.postgres_user, self.postgres_password, self.postgres_db)

    @property
    def database_url(self) -> str:
        """Rol d'aplicació amb permisos limitats, per al servei."""
        return self._url(self.app_db_user, self.app_db_password, self.postgres_db)

    @property
    def database_test_url(self) -> str:
        """Base de dades aïllada per als tests."""
        return self._url(self.postgres_user, self.postgres_password, f"{self.postgres_db}_test")


@lru_cache
def get_settings() -> Settings:
    return Settings()
