import re
import smtplib
from datetime import UTC, datetime, timedelta
from urllib.parse import unquote

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.models import Category, Prompt, Response, Session, User, Vote, Winner
from app.security import (
    compute_email_hash,
    create_email_verification_token,
    hash_session_token,
    verify_email_verification_token,
)
from app.services import email_service
from app.services.auth_service import anonymize_user_rgpd
from tests.conftest import DEFAULT_PASSWORD


@pytest.fixture
def require_email_verification(monkeypatch):
    monkeypatch.setenv("REQUIRE_EMAIL_VERIFICATION", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_register_user_success(client, session):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "nou_usuari@example.com",
            "password": DEFAULT_PASSWORD,
            "consent": True,
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "verified"}

    created_user = session.scalar(select(User).where(User.email == "nou_usuari@example.com"))
    assert created_user is not None
    assert created_user.email_hash == compute_email_hash("nou_usuari@example.com")
    assert created_user.password_hash.startswith("$argon2id$")
    assert created_user.consent_at is not None
    assert created_user.email_verified_at is not None
    assert created_user.qualified_at is None


def test_register_requires_email_verification_when_enabled(
    client, session, require_email_verification
):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "verificacio_obligatoria@example.com",
            "password": DEFAULT_PASSWORD,
            "consent": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "pending_verification"

    created_user = session.scalar(
        select(User).where(User.email == "verificacio_obligatoria@example.com")
    )
    assert created_user is not None
    assert created_user.email_verified_at is None


def test_register_requires_explicit_consent(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "sense_consent@example.com",
            "password": DEFAULT_PASSWORD,
            "consent": False,
        },
    )

    assert response.status_code == 400


def test_register_rejects_invalid_email(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "no-es-un-email",
            "password": DEFAULT_PASSWORD,
            "consent": True,
        },
    )

    assert response.status_code == 422


def test_register_rejects_short_password(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "curta@example.com",
            "password": "curt",
            "consent": True,
        },
    )

    assert response.status_code == 422


def test_verify_email_success(client, session, create_user):
    user = create_user("verificar@example.com", verified=False)

    token = create_email_verification_token(user.id, user.email)
    response = client.post("/api/auth/verify", json={"token": token})

    assert response.status_code == 200
    assert response.json()["status"] == "verified"

    session.refresh(user)
    assert user.email_verified_at is not None


def test_login_success_sets_cookie_and_creates_session(client, session, create_user):
    user = create_user("login_ok@example.com")

    response = client.post(
        "/api/auth/login",
        json={"email": "login_ok@example.com", "password": DEFAULT_PASSWORD},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "logged_in"
    assert "session_token" in response.cookies

    token_hash = hash_session_token(response.cookies["session_token"])
    stored_session = session.scalar(select(Session).where(Session.token_hash == token_hash))
    assert stored_session is not None
    assert stored_session.user_id == user.id
    assert stored_session.revoked_at is None


def test_login_requires_verified_email(client, create_user, require_email_verification):
    create_user("login_unverified@example.com", verified=False)

    response = client.post(
        "/api/auth/login",
        json={"email": "login_unverified@example.com", "password": DEFAULT_PASSWORD},
    )

    assert response.status_code == 403


def test_logout_revokes_session_and_clears_cookie(client, session, create_user, login):
    create_user("logout_ok@example.com")

    login_response = login("logout_ok@example.com")
    raw_token = login_response.cookies.get("session_token")
    assert raw_token is not None

    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 200
    assert logout_response.json()["status"] == "logged_out"

    token_hash = hash_session_token(raw_token)
    stored_session = session.scalar(select(Session).where(Session.token_hash == token_hash))
    assert stored_session is not None
    assert stored_session.revoked_at is not None


def test_logout_without_cookie_returns_logged_out(client, session):
    response = client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.json()["status"] == "logged_out"
    assert session.scalar(select(Session)) is None


def test_delete_account_success_anonymizes_and_revokes_sessions(client, session, logged_in_user):
    user = logged_in_user("delete_ok@example.com")

    response = client.post(
        "/api/auth/delete-account",
        json={"current_password": DEFAULT_PASSWORD},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "deleted"

    session.refresh(user)
    assert user.email is None
    assert user.password_hash is None
    assert user.email_verified_at is None
    assert user.qualified_at is None
    assert user.consent_at is None
    assert user.deleted_at is not None
    assert user.email_hash is None

    user_sessions = session.scalars(select(Session).where(Session.user_id == user.id)).all()
    assert len(user_sessions) > 0
    assert all(s.revoked_at is not None for s in user_sessions)

    reregister_response = client.post(
        "/api/auth/register",
        json={
            "email": "delete_ok@example.com",
            "password": "ContrasenyaNova123!",
            "consent": True,
        },
    )
    assert reregister_response.status_code == 200


def test_delete_account_requires_session(client):
    response = client.post(
        "/api/auth/delete-account",
        json={"current_password": DEFAULT_PASSWORD},
    )

    assert response.status_code == 401


def test_delete_account_requires_correct_password(client, session, logged_in_user):
    user = logged_in_user("delete_wrong_pass@example.com")

    response = client.post(
        "/api/auth/delete-account",
        json={"current_password": "contrasenya_incorrecta"},
    )

    assert response.status_code == 401

    session.refresh(user)
    assert user.deleted_at is None
    assert user.email == "delete_wrong_pass@example.com"
    assert user.password_hash is not None


def test_export_data_returns_user_and_votes(client, session, logged_in_user):
    user = logged_in_user("export_ok@example.com")

    category = Category(code="export_cat", name="Categoria export")
    session.add(category)
    session.commit()

    prompt = Prompt(version="v1", code="export_prompt", category_id=category.id, text="Text prova")
    session.add(prompt)
    session.commit()

    response_a = Response(prompt_id=prompt.id, model="model_A", text="Resposta A")
    response_b = Response(prompt_id=prompt.id, model="model_B", text="Resposta B")
    session.add_all([response_a, response_b])
    session.commit()

    vote = Vote(
        prompt_id=prompt.id,
        user_id=user.id,
        response_a_id=response_a.id,
        response_b_id=response_b.id,
        winner=Winner.a,
        session_id="sessio_export_1",
    )
    session.add(vote)
    session.commit()

    response = client.get("/api/auth/export")
    assert response.status_code == 200

    data = response.json()
    assert data["user"]["id"] == user.id
    assert data["user"]["email"] == "export_ok@example.com"
    assert data["user"]["consent_version"] == "v1"

    assert len(data["votes"]) == 1
    assert data["votes"][0]["prompt_id"] == prompt.id
    assert data["votes"][0]["response_a_id"] == response_a.id
    assert data["votes"][0]["response_b_id"] == response_b.id
    assert data["votes"][0]["winner"] == "a"


def test_export_data_requires_session(client):
    response = client.get("/api/auth/export")

    assert response.status_code == 401


def test_session_returns_authenticated_user(client, logged_in_user):
    logged_in_user("session_ok@example.com")

    response = client.get("/api/auth/session")

    assert response.status_code == 200
    assert response.json() == {
        "authenticated": True,
        "email": "session_ok@example.com",
        "email_verified": True,
        "qualified": True,
    }


def test_session_without_cookie_returns_unauthenticated(client):
    response = client.get("/api/auth/session")

    assert response.status_code == 200
    assert response.json() == {
        "authenticated": False,
        "email": None,
        "email_verified": False,
        "qualified": False,
    }


def test_session_with_invalid_cookie_returns_unauthenticated(client):
    client.cookies.set(get_settings().cookie_name, "token_inventat")

    response = client.get("/api/auth/session")

    assert response.status_code == 200
    assert response.json()["authenticated"] is False


def test_session_after_logout_returns_unauthenticated(client, logged_in_user):
    logged_in_user("session_logout@example.com")

    assert client.post("/api/auth/logout").status_code == 200

    response = client.get("/api/auth/session")
    assert response.status_code == 200
    assert response.json()["authenticated"] is False


def test_session_with_expired_session_returns_unauthenticated(client, session, logged_in_user):
    user = logged_in_user("session_expired@example.com")

    stored_session = session.scalar(select(Session).where(Session.user_id == user.id))
    stored_session.expires_at = datetime.now(UTC) - timedelta(hours=1)
    session.commit()

    response = client.get("/api/auth/session")

    assert response.status_code == 200
    assert response.json()["authenticated"] is False


def test_session_reports_unverified_email(client, create_user, login):
    # Amb REQUIRE_EMAIL_VERIFICATION desactivat l'usuari sense verificar pot iniciar
    # sessió, però el client ha de poder distingir-lo d'un de verificat.
    create_user("session_unverified@example.com", verified=False)
    login("session_unverified@example.com")

    response = client.get("/api/auth/session")

    assert response.status_code == 200
    assert response.json() == {
        "authenticated": True,
        "email": "session_unverified@example.com",
        "email_verified": False,
        "qualified": True,
    }


def test_get_ranking_unkwnown_category(client):
    """Prova què passa quan intentem obtenir el rànquing d'una categoria no existent."""
    category_code = "cat_inexistent"
    response = client.get(f"/api/ranking?category_code={category_code}")
    assert response.status_code == 404
    assert response.json()["detail"] == f"No existeix la categoria: {category_code}."


def test_get_ranking_empty_category(client, session, create_user):
    """Prova què passa quan intentem obtenir el rànquing d'una categoria buida."""
    create_user("sense-vots@example.com")
    # Creem una categoria sense vots
    c = Category(code="test_cat", name="Categoria de prova")
    session.add(c)
    session.commit()

    response = client.get(f"/api/ranking?category_code={c.code}")
    assert response.status_code == 200
    assert response.json()["best_model"] is None
    assert response.json()["ranked_models"] == []
    assert response.json()["status"] == "insufficient_data"
    assert response.json()["confidence"]["p_best_is_best"] is None
    assert response.json()["confidence"]["confidence_interval"] is None
    assert response.json()["confidence"]["is_stable"] is False
    assert response.json()["n_participants"] == 0
    assert client.get("/api/ranking").json()["n_participants"] == 0
    assert client.get("/api/ranking").json()["status"] == "insufficient_data"
    assert "models" not in response.json()
    assert "bt_skills" not in response.json()
    assert "raw_pairwise" not in response.json()
    assert "cycle_detected" not in response.json()
    assert "cycle_path" not in response.json()


def test_get_ranking_full_category(client, session):
    """Prova què passa quan intentem obtenir el rànquing d'una categoria amb vots."""
    # Recuperem la categoria 'correccio'
    c = session.scalar(select(Category).where(Category.code == "correccio"))

    # Inserim dades falses
    p = Prompt(version="v1", code="correccio", category_id=c.id, text="El gat es blau")
    session.add(p)
    session.commit()

    r1 = Response(prompt_id=p.id, model="model_1", text="El gat és blau")
    r2 = Response(prompt_id=p.id, model="model_2", text="El gat es color blau")
    session.add_all([r1, r2])
    session.commit()

    v1 = Vote(prompt_id=p.id, response_a_id=r1.id, response_b_id=r2.id, winner="a")
    session.add(v1)
    session.commit()

    # Obtenim resposta
    response = client.get(f"/api/ranking?category_code={c.code}")
    assert response.status_code == 200
    assert response.json()["best_model"] == "model_1"
    assert response.json()["status"] == "insufficient_data"
    assert response.json()["n_participants"] == 0
    assert response.json()["ranked_models"] == [
        {
            "rank": 1,
            "model": "model_1",
            "bt_skill": response.json()["ranked_models"][0]["bt_skill"],
        },
        {
            "rank": 2,
            "model": "model_2",
            "bt_skill": response.json()["ranked_models"][1]["bt_skill"],
        },
    ]
    assert (
        response.json()["ranked_models"][0]["bt_skill"]
        > response.json()["ranked_models"][1]["bt_skill"]
    )
    assert "models" not in response.json()
    assert "bt_skills" not in response.json()
    assert "raw_pairwise" not in response.json()
    assert "cycle_detected" not in response.json()
    assert "cycle_path" not in response.json()
    assert response.json()["confidence"]["best_model"] == "model_1"
    assert response.json()["confidence"]["n_decisive_votes"] == 1
    assert response.json()["confidence"]["p_best_is_best"] is None
    assert response.json()["confidence"]["confidence_interval"] is None
    assert response.json()["confidence"]["is_stable"] is False
    assert "ci_lo" not in response.json()["confidence"]
    assert "ci_hi" not in response.json()["confidence"]


@pytest.mark.parametrize("winner", [Winner.tie, Winner.neither])
@pytest.mark.parametrize("category_code", [None, "correccio"])
def test_get_ranking_only_non_decisive_votes_is_insufficient(
    client, session, winner, category_code
):
    """Sense vots decisius, no hi ha líder, classificació ni confiança disponible."""
    category = session.scalar(select(Category).where(Category.code == "correccio"))
    prompt = Prompt(version="v1", code="no-decisive", category_id=category.id, text="Text")
    response_a = Response(prompt=prompt, model="model_1", text="Resposta A")
    response_b = Response(prompt=prompt, model="model_2", text="Resposta B")
    session.add_all([prompt, response_a, response_b])
    session.flush()
    session.add(
        Vote(
            prompt_id=prompt.id,
            response_a_id=response_a.id,
            response_b_id=response_b.id,
            winner=winner,
        )
    )
    session.commit()

    params = {"category_code": category_code} if category_code else {}
    response = client.get("/api/ranking", params=params)
    assert response.status_code == 200
    assert response.json()["n_votes_total"] == 1
    assert response.json()["n_votes_decisive"] == 0
    assert response.json()["n_ties"] == int(winner == Winner.tie)
    assert response.json()["n_neither"] == int(winner == Winner.neither)
    assert response.json()["status"] == "insufficient_data"
    assert response.json()["confidence"]["confidence_interval"] is None
    assert response.json()["best_model"] is None
    assert response.json()["confidence"]["best_model"] is None
    assert response.json()["ranked_models"] == []


@pytest.mark.parametrize(
    ("winners", "status"),
    [
        ([Winner.a] * 2, "insufficient_data"),
        ([Winner.a] * 9, "insufficient_data"),
        ([Winner.a] * 10, "stable"),
        ([Winner.a, Winner.b] * 5, "provisional"),
    ],
)
def test_get_ranking_status_depends_on_prompt_coverage_and_confidence(
    client, session, winners, status
):
    """L'API distingeix manca de cobertura, estabilitat i preferències oposades."""
    category = session.scalar(select(Category).where(Category.code == "correccio"))
    for index, winner in enumerate(winners):
        prompt = Prompt(
            version="v1", code=f"opposing-{index}", category_id=category.id, text="Text"
        )
        response_a = Response(prompt=prompt, model="model_1", text="Resposta A")
        response_b = Response(prompt=prompt, model="model_2", text="Resposta B")
        session.add_all([prompt, response_a, response_b])
        session.flush()
        session.add(
            Vote(
                prompt_id=prompt.id,
                response_a_id=response_a.id,
                response_b_id=response_b.id,
                winner=winner,
            )
        )
    session.commit()

    for params in ({}, {"category_code": category.code}):
        response = client.get("/api/ranking", params=params)
        assert response.status_code == 200
        assert response.json()["status"] == status
        interval = response.json()["confidence"]["confidence_interval"]
        if status == "insufficient_data":
            assert interval is None
        elif status == "provisional":
            assert interval["lo"] < 0 < interval["hi"]
        else:
            assert interval["lo"] > 0
        assert response.json()["confidence"]["is_stable"] is (status == "stable")


def test_get_ranking_without_category_returns_global(client, session, create_user):
    """Sense `category_code`, l'API retorna el rànquing global."""
    voter = create_user("diversos-vots@example.com")
    tie_voter = create_user("empat@example.com")
    neither_voter = create_user("cap@example.com")
    correccio = session.scalar(select(Category).where(Category.code == "correccio"))
    traduccio = session.scalar(select(Category).where(Category.code == "traduccio"))

    p1 = Prompt(version="v1", code="global-correccio", category_id=correccio.id, text="Text 1")
    p2 = Prompt(version="v1", code="global-traduccio", category_id=traduccio.id, text="Text 2")
    p3 = Prompt(version="v1", code="global-correccio-2", category_id=correccio.id, text="Text 3")
    session.add_all([p1, p2, p3])
    session.flush()

    r1a = Response(prompt_id=p1.id, model="model_1", text="Resposta 1A")
    r1b = Response(prompt_id=p1.id, model="model_2", text="Resposta 1B")
    r2a = Response(prompt_id=p2.id, model="model_1", text="Resposta 2A")
    r2b = Response(prompt_id=p2.id, model="model_2", text="Resposta 2B")
    r3a = Response(prompt_id=p3.id, model="model_1", text="Resposta 3A")
    r3b = Response(prompt_id=p3.id, model="model_2", text="Resposta 3B")
    session.add_all([r1a, r1b, r2a, r2b, r3a, r3b])
    session.flush()

    session.add_all(
        Vote(
            prompt_id=response_a.prompt_id,
            response_a_id=response_a.id,
            response_b_id=response_b.id,
            user_id=user.id if user else None,
            winner=winner,
        )
        for response_a, response_b, user, winner in [
            (r1a, r1b, voter, Winner.a),
            (r2a, r2b, voter, Winner.a),
            (r3a, r3b, voter, Winner.a),
            (r1a, r1b, tie_voter, Winner.tie),
            (r2a, r2b, neither_voter, Winner.neither),
            (r1a, r1b, None, Winner.a),
        ]
    )
    session.commit()

    response = client.get("/api/ranking")

    assert response.status_code == 200
    assert response.json()["category_code"] is None
    assert response.json()["n_votes_total"] == 6
    assert response.json()["status"] == "insufficient_data"
    assert response.json()["n_participants"] == 3
    assert response.json()["best_model"] == "model_1"
    assert response.json()["ranked_models"][0]["model"] == "model_1"
    assert response.json()["confidence"]["category_code"] is None
    assert response.json()["confidence"]["best_model"] == "model_1"
    assert response.json()["confidence"]["n_decisive_votes"] == 4
    assert response.json()["confidence"]["confidence_interval"] is None
    assert response.json()["confidence"]["is_stable"] is False

    for category_code, expected in [("correccio", 2), ("traduccio", 2), ("reformulacio", 0)]:
        response = client.get("/api/ranking", params={"category_code": category_code})
        assert response.status_code == 200
        assert response.json()["n_participants"] == expected
        assert response.json()["status"] == "insufficient_data"


# --- Enviament del correu de verificació -------------------------------------------------


def _register(client, email: str):
    return client.post(
        "/api/auth/register",
        json={"email": email, "password": DEFAULT_PASSWORD, "consent": True},
    )


def _resend(client, email: str):
    return client.post("/api/auth/resend-verification", json={"email": email})


def _token_from(message) -> str:
    """Extreu el token de l'enllaç de verificació d'un correu enviat."""
    match = re.search(
        r"/verify\?token=(\S+)", message.get_body(preferencelist=("plain",)).get_content()
    )
    assert match is not None
    return unquote(match.group(1))


def test_register_sends_verification_email(client, session, outbox, require_email_verification):
    response = _register(client, "correu_enviat@example.com")

    assert response.status_code == 200
    assert response.json()["status"] == "pending_verification"
    (message,) = outbox
    assert message["To"] == "correu_enviat@example.com"

    user = session.scalar(select(User).where(User.email == "correu_enviat@example.com"))
    assert verify_email_verification_token(_token_from(message))["user_id"] == str(user.id)
    assert user.verification_sent_at is not None


def test_link_from_the_email_completes_verification_and_allows_login(
    client, outbox, require_email_verification
):
    _register(client, "flux_complet@example.com")
    token = _token_from(outbox[0])

    verify = client.post("/api/auth/verify", json={"token": token})
    login = client.post(
        "/api/auth/login",
        json={"email": "flux_complet@example.com", "password": DEFAULT_PASSWORD},
    )

    assert verify.status_code == 200
    assert login.status_code == 200


def test_register_does_not_send_email_when_verification_is_disabled(client, outbox):
    response = _register(client, "sense_correu@example.com")

    assert response.json() == {"status": "verified"}
    assert outbox == []


def test_register_succeeds_even_if_the_mail_server_fails(
    client, session, monkeypatch, require_email_verification
):
    def broken_send(message):
        raise smtplib.SMTPException("servidor caigut")

    monkeypatch.setattr(email_service, "send_email", broken_send)

    response = _register(client, "smtp_caigut@example.com")

    assert response.status_code == 200
    assert response.json()["status"] == "pending_verification"
    assert session.scalar(select(User).where(User.email == "smtp_caigut@example.com"))


def test_resend_sends_a_new_email_to_an_unverified_user(
    client, session, create_user, outbox, require_email_verification
):
    user = create_user("reenviament@example.com", verified=False)

    response = _resend(client, "reenviament@example.com")

    assert response.status_code == 200
    assert response.json()["status"] == "requested"
    (message,) = outbox
    assert message["To"] == "reenviament@example.com"
    assert verify_email_verification_token(_token_from(message))["user_id"] == str(user.id)
    session.refresh(user)
    assert user.verification_sent_at is not None


def test_resend_answers_the_same_for_unknown_and_known_emails(
    client, create_user, outbox, require_email_verification
):
    create_user("existent@example.com", verified=False)

    known = _resend(client, "existent@example.com")
    unknown = _resend(client, "no_existeix@example.com")

    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    assert [message["To"] for message in outbox] == ["existent@example.com"]


def test_register_and_resend_report_the_configured_resend_cooldown(
    client, create_user, monkeypatch, require_email_verification
):
    """El frontend en fa el compte enrere: ha de coincidir amb l'espera real."""
    monkeypatch.setenv("VERIFICATION_RESEND_COOLDOWN_SECONDS", "300")
    get_settings.cache_clear()
    create_user("espera_configurada@example.com", verified=False)

    registered = _register(client, "espera_nova@example.com")
    known = _resend(client, "espera_configurada@example.com")
    unknown = _resend(client, "espera_desconeguda@example.com")

    assert registered.json()["resend_cooldown_seconds"] == 300
    assert known.json() == unknown.json()
    assert known.json()["resend_cooldown_seconds"] == 300


def test_register_does_not_report_a_cooldown_when_no_email_is_sent(client):
    response = _register(client, "sense_espera@example.com")

    assert response.json() == {"status": "verified"}


def test_resend_does_nothing_for_an_already_verified_user(
    client, create_user, outbox, require_email_verification
):
    create_user("ja_verificat@example.com", verified=True)

    response = _resend(client, "ja_verificat@example.com")

    assert response.status_code == 200
    assert outbox == []


def test_resend_does_nothing_for_a_deleted_account(
    client, session, create_user, outbox, require_email_verification
):
    user = create_user("donat_de_baixa@example.com", verified=False)
    anonymize_user_rgpd(user, datetime.now(UTC))
    session.commit()

    response = _resend(client, "donat_de_baixa@example.com")

    assert response.status_code == 200
    assert outbox == []


def test_resend_does_nothing_when_verification_is_disabled(client, create_user, outbox):
    create_user("flag_desactivat@example.com", verified=False)

    response = _resend(client, "flag_desactivat@example.com")

    assert response.status_code == 200
    assert outbox == []


def test_resend_is_silently_limited_by_a_cooldown(
    client, create_user, outbox, require_email_verification
):
    create_user("massa_rapid@example.com", verified=False)

    first = _resend(client, "massa_rapid@example.com")
    second = _resend(client, "massa_rapid@example.com")

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert len(outbox) == 1


def test_resend_is_limited_right_after_registering(client, outbox, require_email_verification):
    _register(client, "just_registrat@example.com")

    response = _resend(client, "just_registrat@example.com")

    assert response.status_code == 200
    assert len(outbox) == 1


def test_resend_works_again_once_the_cooldown_has_passed(
    client, session, create_user, outbox, require_email_verification
):
    user = create_user("passat_el_temps@example.com", verified=False)
    user.verification_sent_at = datetime.now(UTC) - timedelta(minutes=2)
    session.commit()

    _resend(client, "passat_el_temps@example.com")

    assert len(outbox) == 1


def test_resend_rejects_a_malformed_email(client, outbox, require_email_verification):
    response = _resend(client, "no-es-un-correu")

    assert response.status_code == 422
    assert outbox == []


def test_login_with_wrong_password_does_not_reveal_an_unverified_account(
    client, create_user, require_email_verification
):
    create_user("no_revelar@example.com", verified=False)

    wrong_password = client.post(
        "/api/auth/login",
        json={"email": "no_revelar@example.com", "password": "una-altra-contrasenya"},
    )
    unknown_email = client.post(
        "/api/auth/login",
        json={"email": "ningu@example.com", "password": "una-altra-contrasenya"},
    )

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()
