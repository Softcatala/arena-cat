"""Tests de l'script que concedeix i revoca el rol d'administrador (contra PostgreSQL real)."""

import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.services.auth_service import anonymize_user_rgpd

# L'script viu a scripts/ (projecte arrel), fora del paquet backend.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import fes_administrador as script  # noqa: E402


def test_grants_the_role_to_a_verified_account(session, create_user):
    user = create_user("nova@example.com")

    result = script.set_administrator(session, "nova@example.com")

    assert result == script.GRANTED
    session.refresh(user)
    assert user.is_admin is True


def test_email_is_matched_ignoring_case_and_spaces(session, create_user):
    user = create_user("nova@example.com")

    script.set_administrator(session, "  Nova@Example.COM ")

    session.refresh(user)
    assert user.is_admin is True


def test_granting_twice_changes_nothing(session, create_user):
    create_user("nova@example.com")
    script.set_administrator(session, "nova@example.com")

    assert script.set_administrator(session, "nova@example.com") == script.UNCHANGED


def test_only_the_requested_account_is_promoted(session, create_user):
    other = create_user("altra@example.com")
    create_user("nova@example.com")

    script.set_administrator(session, "nova@example.com")

    session.refresh(other)
    assert other.is_admin is False


def test_revoke_removes_the_role(session, create_user):
    user = create_user("nova@example.com")
    script.set_administrator(session, "nova@example.com")

    result = script.set_administrator(session, "nova@example.com", revoke=True)

    assert result == script.REVOKED
    session.refresh(user)
    assert user.is_admin is False


def test_revoking_a_regular_account_changes_nothing(session, create_user):
    create_user("nova@example.com")

    assert script.set_administrator(session, "nova@example.com", revoke=True) == script.UNCHANGED


def test_unknown_account_is_an_error(session):
    with pytest.raises(script.AdministratorError, match="No existeix"):
        script.set_administrator(session, "ningu@example.com")


def test_unverified_account_cannot_be_promoted(session, create_user):
    user = create_user("nova@example.com", verified=False)

    with pytest.raises(script.AdministratorError, match="verificat"):
        script.set_administrator(session, "nova@example.com")

    session.refresh(user)
    assert user.is_admin is False


def test_blocked_account_cannot_be_promoted(session, create_user):
    user = create_user("nova@example.com")
    user.blocked_at = datetime.now(UTC)
    session.commit()

    with pytest.raises(script.AdministratorError, match="bloquejat"):
        script.set_administrator(session, "nova@example.com")


def test_deleted_account_cannot_be_promoted(session, create_user):
    user = create_user("nova@example.com")
    anonymize_user_rgpd(user, datetime.now(UTC))
    session.commit()

    with pytest.raises(script.AdministratorError):
        script.set_administrator(session, "nova@example.com")


def test_revoke_works_on_a_blocked_or_unverified_account(session, create_user):
    user = create_user("nova@example.com")
    script.set_administrator(session, "nova@example.com")
    user.blocked_at = datetime.now(UTC)
    session.commit()

    assert script.set_administrator(session, "nova@example.com", revoke=True) == script.REVOKED


@pytest.fixture
def use_test_session(session, monkeypatch):
    """Fa que `main` treballi amb la sessió de prova en lloc de crear-ne una de pròpia."""

    class Factory:
        def __call__(self):
            return self

        def __enter__(self):
            return session

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(script, "get_sessionmaker", lambda: Factory())


def test_main_grants_and_reports(use_test_session, session, create_user, capsys):
    user = create_user("nova@example.com")

    assert script.main(["nova@example.com"]) == 0

    session.refresh(user)
    assert user.is_admin is True
    assert "administrador" in capsys.readouterr().out


def test_main_revokes(use_test_session, session, create_user):
    user = create_user("nova@example.com")
    script.main(["nova@example.com"])

    assert script.main(["nova@example.com", "--revoca"]) == 0

    session.refresh(user)
    assert user.is_admin is False


def test_main_fails_with_a_nonzero_status_on_error(use_test_session, capsys):
    assert script.main(["ningu@example.com"]) == 1
    assert "No existeix" in capsys.readouterr().err
