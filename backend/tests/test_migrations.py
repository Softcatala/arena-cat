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
