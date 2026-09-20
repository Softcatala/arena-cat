"""Reversibilitat de la migració inicial contra una base de dades efímera."""

import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from app.config import get_settings

_BACKEND = Path(__file__).resolve().parents[1]
TABLES = {
    "categories",
    "prompts",
    "responses",
    "votes",
    "users",
    "sessions",
    "task_skips",
}
ENUMS = {"winner"}


@pytest.fixture
def ephemeral_db_url():
    """Crea una base de dades nova per a la prova i l'esborra al final."""
    admin_url = make_url(get_settings().database_admin_url)
    name = f"arena_cat_migr_{uuid.uuid4().hex[:8]}"
    engine = create_engine(admin_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    try:
        yield admin_url.set(database=name)
    finally:
        with engine.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        engine.dispose()


def _alembic_config(url):
    config = Config(str(_BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(_BACKEND / "migrations"))
    config.set_main_option("sqlalchemy.url", url.render_as_string(hide_password=False))
    return config


def _enums(engine) -> set[str]:
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT typname FROM pg_type WHERE typtype = 'e'"))
        return {row[0] for row in rows}


def test_initial_migration_is_reversible(ephemeral_db_url):
    config = _alembic_config(ephemeral_db_url)
    engine = create_engine(ephemeral_db_url)
    try:
        command.upgrade(config, "head")
        assert TABLES.issubset(inspect(engine).get_table_names())
        assert ENUMS.issubset(_enums(engine))

        command.downgrade(config, "base")
        assert TABLES.isdisjoint(inspect(engine).get_table_names())
        assert ENUMS.isdisjoint(_enums(engine))
    finally:
        engine.dispose()


def test_qualification_migration_preserves_existing_users(ephemeral_db_url):
    """L'acreditació és nul·la per als usuaris existents i la migració és reversible."""
    config = _alembic_config(ephemeral_db_url)
    engine = create_engine(ephemeral_db_url)
    try:
        command.upgrade(config, "e7b2c8a91f04")
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO users "
                    "(email, email_hash, password_hash, consent_version, consent_at) "
                    "VALUES ('existing@example.com', 'hash', 'password', 'v1', now())"
                )
            )
        command.upgrade(config, "head")
        with engine.connect() as connection:
            row = connection.execute(text("SELECT email, qualified_at FROM users")).one()
            assert row == ("existing@example.com", None)
        command.downgrade(config, "e7b2c8a91f04")
        assert "qualified_at" not in {
            column["name"] for column in inspect(engine).get_columns("users")
        }
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT email FROM users")) == "existing@example.com"
        command.upgrade(config, "head")
        assert "qualified_at" in {column["name"] for column in inspect(engine).get_columns("users")}
        command.check(config)
    finally:
        engine.dispose()
