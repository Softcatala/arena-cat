"""Tests del servei d'enviament de correu. SMTP està simulat: no hi ha xarxa."""

import logging
import smtplib

import pytest

from app.config import get_settings
from app.security import create_email_verification_token, verify_email_verification_token
from app.services import email_service


class FakeSMTP:
    """Substitut de `smtplib.SMTP` que enregistra les crides que rep."""

    instances: list["FakeSMTP"] = []
    error: Exception | None = None

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
    assert message["Subject"] == "Verifica el teu correu d'Arena Cat"
    body = message.get_content()
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
    assert f"/verify?token={token}" in message.get_content()
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


def test_smtp_password_is_not_exposed_in_settings(smtp_env):
    smtp_env(SMTP_PASSWORD="contrasenya-molt-secreta")

    assert "contrasenya-molt-secreta" not in repr(get_settings())
