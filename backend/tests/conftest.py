"""Configuració dels tests: motor cap a arena_cat_test i sessió aïllada per test.

Cada test s'executa dins d'una transacció que es desfà al final (rollback),
de manera que queden aïllats entre si.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import models  # noqa: F401  -- registra els models al metadata de Base
from app.config import get_settings
from app.db import Base


@pytest.fixture(scope="session")
def engine():
    """Motor cap a la base de dades de tests; crea l'esquema un sol cop."""
    settings = get_settings()
    eng = create_engine(settings.database_test_url, future=True)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def session(engine):
    """Sessió embolcallada en una transacció externa que es desfà sempre."""
    connection = engine.connect()
    transaction = connection.begin()
    sess = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield sess
    finally:
        sess.close()
        transaction.rollback()
        connection.close()
