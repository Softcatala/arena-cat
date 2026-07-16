"""Configuració de l'aplicació, llegida de variables d'entorn o del fitxer .env."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

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
    # Secret específic per signar/hashar tokens de sessió.
    session_secret: str
    # Pepper per derivar email_hash i detectar re-registres.
    email_hash_pepper: str
    # Versió de consentiment acceptada al registre.
    consent_version: str = "v1"
    # Orígens CORS permesos (separats per comes) quan usem cookies de sessió.
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000"
    # Configuració de la cookie i la sessió d'autenticació.
    session_ttl_hours: int = 24
    cookie_name: str = "session_token"
    cookie_secure: bool = False  # Cal posar-ho a True a producció amb HTTPS.
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

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

    @property
    def cors_origins_list(self) -> list[str]:
        """Llista d'orígens CORS obtinguda de `cors_origins`."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def cookie_max_age(self) -> int:
        """Durada de la cookie de sessió en segons, derivada del TTL de sessió."""
        return self.session_ttl_hours * 3600


@lru_cache
def get_settings() -> Settings:
    return Settings()
