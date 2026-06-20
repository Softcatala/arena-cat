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
TAULES = {"categories", "prompts", "respostes", "vots"}
ENUMS = {"guanyador"}


@pytest.fixture
def url_bd_efimera():
    """Crea una base de dades nova per a la prova i l'esborra al final."""
    admin_url = make_url(get_settings().database_admin_url)
    nom = f"arena_cat_migr_{uuid.uuid4().hex[:8]}"
    motor = create_engine(admin_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with motor.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{nom}"'))
    try:
        yield admin_url.set(database=nom)
    finally:
        with motor.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{nom}" WITH (FORCE)'))
        motor.dispose()


def _config_alembic(url):
    config = Config(str(_BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(_BACKEND / "migrations"))
    config.set_main_option("sqlalchemy.url", url.render_as_string(hide_password=False))
    return config


def _enums(engine) -> set[str]:
    with engine.connect() as conn:
        files = conn.execute(text("SELECT typname FROM pg_type WHERE typtype = 'e'"))
        return {fila[0] for fila in files}


def test_migracio_inicial_es_reversible(url_bd_efimera):
    config = _config_alembic(url_bd_efimera)
    engine = create_engine(url_bd_efimera)
    try:
        command.upgrade(config, "head")
        assert TAULES.issubset(inspect(engine).get_table_names())
        assert ENUMS.issubset(_enums(engine))

        command.downgrade(config, "base")
        assert TAULES.isdisjoint(inspect(engine).get_table_names())
        assert ENUMS.isdisjoint(_enums(engine))
    finally:
        engine.dispose()
