"""Enviament de correu transaccional per SMTP."""

import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from urllib.parse import quote

from app.config import get_settings
from app.security import EMAIL_VERIFICATION_TTL_HOURS, PASSWORD_RESET_TTL_MINUTES

logger = logging.getLogger(__name__)

SMTP_TIMEOUT_SECONDS = 10


def _build_link(path: str, token: str) -> str:
    """Enllaç del frontend que porta el token."""
    base_url = get_settings().frontend_base_url.rstrip("/")
    return f"{base_url}/{path}?token={quote(token, safe='')}"


def _new_message(to_email: str, subject: str) -> EmailMessage:
    """Missatge amb les capçaleres comunes: remitent, destinatari, assumpte i data."""
    settings = get_settings()
    message = EmailMessage()
    message["From"] = formataddr((settings.email_from_name, settings.email_from_address))
    message["To"] = to_email
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid(domain=settings.email_from_address.rpartition("@")[2])
    return message


def build_verification_link(token: str) -> str:
    """Enllaç del frontend que porta el token de verificació."""
    return _build_link("verify", token)


def build_verification_message(to_email: str, link: str) -> EmailMessage:
    """Compon el correu que convida a confirmar l'adreça amb l'enllaç donat."""
    message = _new_message(to_email, "Verifica el teu correu d'Arena Cat")
    message.set_content(
        "Hola!\n\n"
        "Gràcies per registrar-te a Arena Cat, la plataforma de Softcatalà per avaluar "
        "models d'IA en català.\n\n"
        "Per activar el compte, confirma l'adreça de correu amb aquest enllaç "
        f"(caduca d'aquí a {EMAIL_VERIFICATION_TTL_HOURS} hores):\n\n"
        f"{link}\n\n"
        "Si no t'has registrat tu, pots ignorar aquest missatge.\n\n"
        "Softcatalà\n"
    )
    return message


def build_password_reset_link(token: str) -> str:
    """Enllaç del frontend que porta el token de restabliment de contrasenya."""
    return _build_link("reset-password", token)


def build_password_reset_message(to_email: str, link: str) -> EmailMessage:
    """Compon el correu que convida a triar una contrasenya nova amb l'enllaç donat."""
    if PASSWORD_RESET_TTL_MINUTES % 60 == 0:
        hours = PASSWORD_RESET_TTL_MINUTES // 60
        validity = f"{hours} {'hora' if hours == 1 else 'hores'}"
    else:
        validity = f"{PASSWORD_RESET_TTL_MINUTES} minuts"
    message = _new_message(to_email, "Restableix la contrasenya d'Arena Cat")
    message.set_content(
        "Hola!\n\n"
        "Hem rebut una sol·licitud per restablir la contrasenya del teu compte d'Arena Cat.\n\n"
        f"Per triar-ne una de nova, obre aquest enllaç (caduca d'aquí a {validity}):\n\n"
        f"{link}\n\n"
        "Si no ho has demanat tu, pots ignorar aquest missatge: la teva contrasenya "
        "actual no canviarà.\n\n"
        "Softcatalà\n"
    )
    return message


def send_email(message: EmailMessage) -> None:
    """Envia el missatge pel servidor SMTP configurat.

    Sense `smtp_host` no obre cap connexió: deixa el missatge al log perquè es pugui
    provar el flux en local.
    """
    settings = get_settings()
    if not settings.smtp_host:
        logger.warning(
            "SMTP no configurat; no s'envia el correu per a %s:\n%s",
            message["To"],
            message.get_content(),
        )
        return

    context = ssl.create_default_context()
    if settings.smtp_security == "ssl":
        connection = smtplib.SMTP_SSL(
            settings.smtp_host, settings.smtp_port, timeout=SMTP_TIMEOUT_SECONDS, context=context
        )
    else:
        connection = smtplib.SMTP(
            settings.smtp_host, settings.smtp_port, timeout=SMTP_TIMEOUT_SECONDS
        )

    with connection:
        if settings.smtp_security == "starttls":
            connection.ehlo()
            connection.starttls(context=context)
            connection.ehlo()
        if settings.smtp_user:
            connection.login(settings.smtp_user, settings.smtp_password.get_secret_value())
        connection.send_message(message)


def _describe(error: OSError) -> str:
    """Tipus d'error i, si n'hi ha, codi SMTP, per al log.

    No inclou el text de l'excepció ni el traceback: `SMTPRecipientsRefused` i altres
    hi porten l'adreça del destinatari.
    """
    code = getattr(error, "smtp_code", None)
    name = type(error).__name__
    return f"{name} (codi SMTP {code})" if code else name


def _send_quietly(message: EmailMessage, description: str) -> None:
    """Envia el missatge sense propagar errors: s'executa en segon pla.

    Un servidor de correu caigut no ha d'impedir l'operació que l'ha provocat; la
    persona pot demanar un reenviament. No es registra l'adreça ni el text de l'error
    per no deixar dades personals als logs.
    """
    try:
        send_email(message)
    except OSError as error:  # Inclou smtplib.SMTPException, errors de connexió i temps d'espera.
        logger.error("No s'ha pogut enviar el correu de %s: %s", description, _describe(error))


def send_verification_email(to_email: str, token: str) -> None:
    """Envia el correu de verificació de l'adreça."""
    link = build_verification_link(token)
    _send_quietly(build_verification_message(to_email, link), "verificació")


def send_password_reset_email(to_email: str, token: str) -> None:
    """Envia el correu de restabliment de contrasenya."""
    link = build_password_reset_link(token)
    _send_quietly(build_password_reset_message(to_email, link), "restabliment de contrasenya")
