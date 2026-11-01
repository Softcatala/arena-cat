"""Reversibilitat de la migració inicial contra una base de dades efímera."""

import hashlib
import logging
import uuid
from io import StringIO
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, engine_from_config, inspect, text
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
    "qualification_failures",
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
    config.set_main_option(
        "sqlalchemy.url", url.render_as_string(hide_password=False).replace("%", "%%")
    )
    return config


def _enums(engine) -> set[str]:
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT typname FROM pg_type WHERE typtype = 'e'"))
        return {row[0] for row in rows}


@pytest.mark.parametrize("password", ["p@ssword", "p%ssword", "p:/?#[]@% word"])
@pytest.mark.parametrize("explicit_url", [False, True])
def test_migration_url_preserves_special_password(monkeypatch, password, explicit_url):
    """Alembic conserva la contrasenya tant des de l'entorn com amb una URL explícita."""
    monkeypatch.setenv("POSTGRES_PASSWORD", password)
    url = make_url(get_settings().database_admin_url)
    config = _alembic_config(url) if explicit_url else Config(str(_BACKEND / "alembic.ini"))
    config.output_buffer = StringIO()

    command.upgrade(config, "base", sql=True)

    assert make_url(config.get_main_option("sqlalchemy.url")).password == password
    engine = engine_from_config(config.get_section(config.config_ini_section), prefix="sqlalchemy.")
    try:
        assert engine.url.password == password
    finally:
        engine.dispose()


def test_initial_migration_is_reversible(ephemeral_db_url):
    config = _alembic_config(ephemeral_db_url)
    engine = create_engine(ephemeral_db_url)
    try:
        command.upgrade(config, "head")
        assert TABLES.issubset(inspect(engine).get_table_names())
        assert "email_deliveries" not in inspect(engine).get_table_names()
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


def test_migrations_keep_application_loggers_enabled():
    """La configuració d’Alembic conserva els logs de l’aplicació."""
    logger = logging.getLogger("app.services.reminder_service")
    logger.disabled = False
    config = _alembic_config(make_url(get_settings().database_admin_url))
    config.output_buffer = StringIO()
    command.upgrade(config, "base", sql=True)
    assert not logger.disabled


def test_admin_migration_defaults_existing_users_and_is_reversible(ephemeral_db_url):
    """Els usuaris existents no són administradors ni estan bloquejats."""
    config = _alembic_config(ephemeral_db_url)
    engine = create_engine(ephemeral_db_url)
    try:
        command.upgrade(config, "d9f012345678")
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
            row = connection.execute(text("SELECT is_admin, blocked_at FROM users")).one()
            assert row == (False, None)
        command.check(config)
        command.downgrade(config, "d9f012345678")
        columns = {column["name"] for column in inspect(engine).get_columns("users")}
        assert {"is_admin", "blocked_at"}.isdisjoint(columns)
    finally:
        engine.dispose()


def test_prompt_hash_migration_backfills_existing_prompts(ephemeral_db_url):
    """Els prompts existents reben l'empremta SHA-256 del seu text i la migració és reversible."""
    config = _alembic_config(ephemeral_db_url)
    engine = create_engine(ephemeral_db_url)
    try:
        command.upgrade(config, "a1b2c3d4e5f6")
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO categories (code, name) VALUES ('correccio', 'Correcció');"
                    "INSERT INTO prompts (version, code, category_id, text) "
                    "SELECT 'v1', 'correccio_1', id, 'Hola' FROM categories"
                )
            )
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT content_sha256 FROM prompts")) == (
                hashlib.sha256(b"Hola").hexdigest()
            )
        command.check(config)
        command.downgrade(config, "a1b2c3d4e5f6")
        columns = {column["name"] for column in inspect(engine).get_columns("prompts")}
        assert "content_sha256" not in columns
    finally:
        engine.dispose()


def test_response_flags_migration_keeps_existing_responses_active(ephemeral_db_url):
    """Les respostes existents queden actives i incloses al rànquing; la migració és reversible."""
    config = _alembic_config(ephemeral_db_url)
    engine = create_engine(ephemeral_db_url)
    try:
        command.upgrade(config, "b2c3d4e5f6a7")
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO categories (code, name) VALUES ('correccio', 'Correcció');"
                    "INSERT INTO prompts (version, code, category_id, text, content_sha256) "
                    f"SELECT 'v1', 'correccio_1', id, 'Hola', '{'a' * 64}' FROM categories;"
                    "INSERT INTO responses (prompt_id, model, text) "
                    "SELECT id, 'model-a', 'Resposta' FROM prompts"
                )
            )
        command.upgrade(config, "head")
        with engine.connect() as connection:
            row = connection.execute(
                text("SELECT active, included_in_ranking FROM responses")
            ).one()
            assert row == (True, True)
        command.check(config)
        command.downgrade(config, "b2c3d4e5f6a7")
        columns = {column["name"] for column in inspect(engine).get_columns("responses")}
        assert {"active", "included_in_ranking", "updated_at"}.isdisjoint(columns)
    finally:
        engine.dispose()


def test_prompt_active_migration_keeps_existing_prompts_active(ephemeral_db_url):
    """Els prompts existents queden actius i la migració és reversible."""
    config = _alembic_config(ephemeral_db_url)
    engine = create_engine(ephemeral_db_url)
    try:
        command.upgrade(config, "c3d4e5f6a7b8")
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO categories (code, name) VALUES ('correccio', 'Correcció');"
                    "INSERT INTO prompts (version, code, category_id, text, content_sha256) "
                    f"SELECT 'v1', 'correccio_1', id, 'Hola', '{'a' * 64}' FROM categories"
                )
            )
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT active FROM prompts")) is True
        command.check(config)
        command.downgrade(config, "c3d4e5f6a7b8")
        columns = {column["name"] for column in inspect(engine).get_columns("prompts")}
        assert {"active", "updated_at"}.isdisjoint(columns)
    finally:
        engine.dispose()
