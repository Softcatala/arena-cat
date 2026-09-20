"""Tests del servei d'enviament de correu. SMTP està simulat: no hi ha xarxa."""

import logging
import smtplib

import pytest

from app.config import get_settings
from app.security import (
    create_email_verification_token,
    create_password_reset_token,
    verify_email_verification_token,
)
from app.services import email_service


def plain(message) -> str:
    """Cos en text pla d'un missatge amb versió de text i d'HTML."""
    return message.get_body(preferencelist=("plain",)).get_content()


def html(message) -> str:
    return message.get_body(preferencelist=("html",)).get_content()


class FakeSMTP:
    """Substitut de `smtplib.SMTP` que enregistra les crides que rep."""

    instances: list["FakeSMTP"] = []
    error: Exception | None = None
    # Si el servidor anuncia l'extensió AUTH (com fa des de fora de la xarxa interna).
    auth_supported = True

    def __init__(self, host, port, timeout=None, context=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.context = context
        self.calls: list = []
        self.sent: list = []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def ehlo(self):
        self.calls.append("ehlo")

    def starttls(self, context=None):
        self.calls.append("starttls")

    def ehlo_or_helo_if_needed(self):
        pass

    def has_extn(self, name):
        return FakeSMTP.auth_supported if name.lower() == "auth" else True

    def login(self, user, password):
        self.calls.append(("login", user, password))

    def send_message(self, message):
        if FakeSMTP.error is not None:
            raise FakeSMTP.error
        self.sent.append(message)


class FakeSMTPSSL(FakeSMTP):
    """Substitut de `smtplib.SMTP_SSL`."""


@pytest.fixture
def fake_smtp(monkeypatch):
    FakeSMTP.instances = []
    FakeSMTP.error = None
    FakeSMTP.auth_supported = True
    monkeypatch.setattr(email_service.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(email_service.smtplib, "SMTP_SSL", FakeSMTPSSL)
    return FakeSMTP


@pytest.fixture
def smtp_env(monkeypatch):
    """Configura el SMTP de proves; accepta valors per sobreescriure."""

    def _configure(**overrides):
        values = {
            "SMTP_HOST": "smtp.example.org",
            "SMTP_PORT": "587",
            "SMTP_SECURITY": "starttls",
            "SMTP_USER": "arena",
            "SMTP_PASSWORD": "secret",
            "EMAIL_FROM_ADDRESS": "arena@example.org",
            "EMAIL_FROM_NAME": "Arena Cat",
            "FRONTEND_BASE_URL": "https://arena.example.org/",
        }
        values.update(overrides)
        for key, value in values.items():
            monkeypatch.setenv(key, value)
        get_settings.cache_clear()

    yield _configure
    get_settings.cache_clear()


def test_verification_link_uses_frontend_base_url(smtp_env):
    smtp_env(FRONTEND_BASE_URL="https://arena.example.org/")

    link = email_service.build_verification_link("abc.def_ghi-jkl")

    assert link == "https://arena.example.org/verify?token=abc.def_ghi-jkl"


def test_verification_link_escapes_the_token(smtp_env):
    smtp_env()

    link = email_service.build_verification_link("a b&c=d")

    assert link.endswith("/verify?token=a%20b%26c%3Dd")


def test_verification_message_headers_and_body(smtp_env):
    smtp_env()

    message = email_service.build_verification_message(
        "usuari@example.com", "https://arena.example.org/verify?token=xyz"
    )

    assert message["To"] == "usuari@example.com"
    assert message["From"] == "Arena Cat <arena@example.org>"
    assert message["Subject"] == "Verifiqueu el vostre correu d'Arena Cat"
    body = plain(message)
    assert "https://arena.example.org/verify?token=xyz" in body
    assert "24 hores" in body


def test_send_email_with_starttls_logs_in_and_sends(smtp_env, fake_smtp):
    smtp_env()
    message = email_service.build_verification_message("usuari@example.com", "https://x/verify")

    email_service.send_email(message)

    (connection,) = fake_smtp.instances
    assert type(connection) is FakeSMTP
    assert (connection.host, connection.port) == ("smtp.example.org", 587)
    assert connection.timeout is not None
    assert connection.calls == ["ehlo", "starttls", "ehlo", ("login", "arena", "secret")]
    assert connection.sent == [message]


def test_send_email_with_ssl_does_not_use_starttls(smtp_env, fake_smtp):
    smtp_env(SMTP_SECURITY="ssl", SMTP_PORT="465")
    message = email_service.build_verification_message("usuari@example.com", "https://x/verify")

    email_service.send_email(message)

    (connection,) = fake_smtp.instances
    assert type(connection) is FakeSMTPSSL
    assert connection.port == 465
    assert "starttls" not in connection.calls
    assert ("login", "arena", "secret") in connection.calls
    assert connection.sent == [message]


def test_send_email_without_security_or_credentials(smtp_env, fake_smtp):
    smtp_env(SMTP_SECURITY="none", SMTP_USER="", SMTP_PASSWORD="", SMTP_PORT="1025")
    message = email_service.build_verification_message("usuari@example.com", "https://x/verify")

    email_service.send_email(message)

    (connection,) = fake_smtp.instances
    assert connection.calls == []
    assert connection.sent == [message]


def test_send_email_without_smtp_host_only_logs_the_link(fake_smtp, caplog):
    caplog.set_level(logging.INFO)
    message = email_service.build_verification_message(
        "usuari@example.com", "https://arena.example.org/verify?token=xyz"
    )

    email_service.send_email(message)

    assert fake_smtp.instances == []
    assert "https://arena.example.org/verify?token=xyz" in caplog.text


def test_send_verification_email_sends_a_message_with_a_valid_token(smtp_env, fake_smtp):
    smtp_env()
    token = create_email_verification_token(7, "usuari@example.com")

    email_service.send_verification_email("usuari@example.com", token)

    (connection,) = fake_smtp.instances
    (message,) = connection.sent
    assert message["To"] == "usuari@example.com"
    assert f"/verify?token={token}" in plain(message)
    assert verify_email_verification_token(token)["user_id"] == "7"


@pytest.mark.parametrize(
    "error",
    [smtplib.SMTPException("boom"), ConnectionRefusedError("down"), TimeoutError("slow")],
)
def test_send_verification_email_never_raises(smtp_env, fake_smtp, caplog, error):
    smtp_env()
    fake_smtp.error = error

    email_service.send_verification_email("usuari@example.com", "token")

    assert "No s'ha pogut enviar" in caplog.text


@pytest.mark.parametrize(
    "error",
    [
        smtplib.SMTPRecipientsRefused({"usuari@example.com": (550, b"no such user")}),
        smtplib.SMTPResponseException(550, "usuari@example.com: mailbox unavailable"),
        OSError("no s'ha pogut arribar a usuari@example.com"),
    ],
)
def test_send_failure_log_does_not_contain_the_address(smtp_env, fake_smtp, caplog, error):
    """El text i el traceback d'una excepció SMTP poden dur l'adreça del destinatari."""
    smtp_env()
    fake_smtp.error = error

    email_service.send_verification_email("usuari@example.com", "token")

    assert "usuari@example.com" not in caplog.text
    assert "Traceback" not in caplog.text
    assert type(error).__name__ in caplog.text


def test_send_failure_log_includes_the_smtp_code(smtp_env, fake_smtp, caplog):
    smtp_env()
    fake_smtp.error = smtplib.SMTPResponseException(554, "rebutjat")

    email_service.send_verification_email("usuari@example.com", "token")

    assert "554" in caplog.text


def test_smtp_password_is_not_exposed_in_settings(smtp_env):
    smtp_env(SMTP_PASSWORD="contrasenya-molt-secreta")

    assert "contrasenya-molt-secreta" not in repr(get_settings())


def test_password_reset_link_uses_frontend_base_url(smtp_env):
    smtp_env(FRONTEND_BASE_URL="https://arena.example.org/")

    link = email_service.build_password_reset_link("abc.def_ghi-jkl")

    assert link == "https://arena.example.org/reset-password?token=abc.def_ghi-jkl"


def test_password_reset_message_headers_and_body(smtp_env):
    smtp_env()

    message = email_service.build_password_reset_message(
        "usuari@example.com", "https://arena.example.org/reset-password?token=xyz"
    )

    assert message["To"] == "usuari@example.com"
    assert message["From"] == "Arena Cat <arena@example.org>"
    assert message["Subject"] == "Restabliment de la contrasenya d'Arena Cat"
    body = plain(message)
    assert "https://arena.example.org/reset-password?token=xyz" in body
    assert "1 hora" in body


def test_send_password_reset_email_sends_a_message_with_a_valid_token(smtp_env, fake_smtp):
    smtp_env()
    token = create_password_reset_token(7, "hash-actual")

    email_service.send_password_reset_email("usuari@example.com", token)

    (connection,) = fake_smtp.instances
    (message,) = connection.sent
    assert message["To"] == "usuari@example.com"
    assert f"/reset-password?token={token}" in plain(message)


def test_send_password_reset_email_never_raises(smtp_env, fake_smtp, caplog):
    smtp_env()
    fake_smtp.error = smtplib.SMTPException("boom")

    email_service.send_password_reset_email("usuari@example.com", "token")

    assert "No s'ha pogut enviar" in caplog.text


@pytest.mark.parametrize(
    ("security", "port"), [("starttls", "587"), ("ssl", "465"), ("none", "25")]
)
def test_send_email_skips_the_login_when_the_server_does_not_offer_auth(
    smtp_env, fake_smtp, caplog, security, port
):
    """Un servidor de la xarxa interna pot no anunciar AUTH: llavors s'envia sense autenticar."""
    smtp_env(SMTP_SECURITY=security, SMTP_PORT=port)
    fake_smtp.auth_supported = False
    message = email_service.build_verification_message("usuari@example.com", "https://x/verify")

    email_service.send_email(message)

    (connection,) = fake_smtp.instances
    assert not any(isinstance(call, tuple) and call[0] == "login" for call in connection.calls)
    assert connection.sent == [message]
    assert "no anuncia AUTH" in caplog.text


def test_send_email_does_not_warn_about_auth_when_the_server_offers_it(smtp_env, fake_smtp, caplog):
    smtp_env()
    message = email_service.build_verification_message("usuari@example.com", "https://x/verify")

    email_service.send_email(message)

    (connection,) = fake_smtp.instances
    assert ("login", "arena", "secret") in connection.calls
    assert "no anuncia AUTH" not in caplog.text


def test_send_email_does_not_warn_about_auth_when_no_user_is_configured(
    smtp_env, fake_smtp, caplog
):
    smtp_env(SMTP_USER="", SMTP_PASSWORD="")
    fake_smtp.auth_supported = False
    message = email_service.build_verification_message("usuari@example.com", "https://x/verify")

    email_service.send_email(message)

    assert "no anuncia AUTH" not in caplog.text


@pytest.mark.parametrize("kind", ["verification", "password_reset"])
def test_emails_say_they_are_automatic_and_replies_are_not_read(smtp_env, kind):
    smtp_env()
    build = {
        "verification": email_service.build_verification_message,
        "password_reset": email_service.build_password_reset_message,
    }[kind]

    body = plain(build("usuari@example.com", "https://arena.example.org/x?token=t"))

    assert "Aquest és un correu automàtic" in body
    assert "les respostes no es processen" in body
    # L'avís va al final, per sota de la signatura, com els peus habituals.
    assert body.rstrip().endswith("les respostes no es processen.")


@pytest.mark.parametrize("kind", ["verification", "password_reset"])
def test_emails_have_a_plain_text_and_an_html_version(smtp_env, kind):
    smtp_env()
    build = {
        "verification": email_service.build_verification_message,
        "password_reset": email_service.build_password_reset_message,
    }[kind]

    message = build("usuari@example.com", "https://arena.example.org/x?token=t")

    assert message.get_content_type() == "multipart/alternative"
    # El text pla va primer: els clients mostren la darrera versió que entenen.
    assert [part.get_content_type() for part in message.iter_parts()] == [
        "text/plain",
        "text/html",
    ]


@pytest.mark.parametrize("kind", ["verification", "password_reset"])
def test_html_email_has_the_link_as_a_button_and_as_visible_text(smtp_env, kind):
    smtp_env()
    build = {
        "verification": email_service.build_verification_message,
        "password_reset": email_service.build_password_reset_message,
    }[kind]
    link = "https://arena.example.org/x?token=abc"

    body = html(build("usuari@example.com", link))

    # El botó porta a l'enllaç i, per als clients que amaguen botons, també es veu escrit.
    assert f'href="{link}"' in body
    assert body.count(link) >= 2
    assert "#E64B3C" in body
    assert "© Softcatalà" in body
    assert "Aquest és un correu automàtic" in body


def test_html_email_escapes_the_values_it_inserts(smtp_env):
    smtp_env()
    dangerous = 'https://arena.example.org/x?a=1&b="><script>alert(1)</script>'

    body = html(email_service.build_verification_message("usuari@example.com", dangerous))

    assert "<script>" not in body
    assert "&lt;script&gt;" in body
    # El text pla no s'escapa: no és HTML.
    assert dangerous in plain(email_service.build_verification_message("u@example.com", dangerous))


@pytest.mark.parametrize("kind", ["verification", "password_reset"])
def test_emails_address_the_reader_formally(smtp_env, kind):
    smtp_env()
    build = {
        "verification": email_service.build_verification_message,
        "password_reset": email_service.build_password_reset_message,
    }[kind]

    body = plain(build("usuari@example.com", "https://arena.example.org/x?token=t"))

    assert "vostre" in body
    assert "podeu ignorar" in body
    for informal in ("teu ", "pots ", "t'has ", "confirma "):
        assert informal not in body


def test_password_reset_email_warns_not_to_share_the_link(smtp_env):
    smtp_env()

    message = email_service.build_password_reset_message(
        "usuari@example.com", "https://arena.example.org/reset-password?token=xyz"
    )

    assert "No compartiu aquest enllaç" in plain(message)
    assert "No compartiu aquest enllaç" in html(message)
