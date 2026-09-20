"""Enviament de correu transaccional per SMTP."""

import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from app.config import get_settings
from app.security import EMAIL_VERIFICATION_TTL_HOURS, PASSWORD_RESET_TTL_MINUTES

logger = logging.getLogger(__name__)

SMTP_TIMEOUT_SECONDS = 10

# Peu comú dels correus: ningú llegeix les respostes a l'adreça remitent.
AUTOMATIC_NOTICE = (
    "Aquest és un correu automàtic. Si us plau, no respongueu a aquest missatge: "
    "les respostes no es processen."
)

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "email_templates"


@lru_cache
def _templates() -> Environment:
    """Plantilles dels correus. Només s'escapa l'HTML: el text pla no és HTML.

    `StrictUndefined` fa fallar un correu amb una variable que falta, en comptes de
    enviar-lo amb un forat.
    """
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html"]),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )


def _set_body(message: EmailMessage, template: str, **context: object) -> None:
    """Omple el missatge amb la versió en text pla i, com a alternativa, la d'HTML.

    El text pla va primer: els clients mostren l'última versió que entenen.
    """
    environment = _templates()
    context = {"notice": AUTOMATIC_NOTICE, **context}
    message.set_content(environment.get_template(f"{template}.txt").render(context))
    message.add_alternative(
        environment.get_template(f"{template}.html").render(context), subtype="html"
    )


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
    message = _new_message(to_email, "Verifiqueu el vostre correu d'Arena Cat")
    _set_body(message, "verification", link=link, hours=EMAIL_VERIFICATION_TTL_HOURS)
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
    message = _new_message(to_email, "Restabliment de la contrasenya d'Arena Cat")
    _set_body(message, "password-reset", link=link, validity=validity)
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
            message.get_body(preferencelist=("plain",)).get_content(),
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
            # Un servidor pot no oferir AUTH a certs clients (p. ex. a la xarxa interna, on
            # accepta el correu sense credencials). Intentar-hi entrar només donaria un
            # error, així que s'envia sense autenticar i es deixa un avís al log.
            connection.ehlo_or_helo_if_needed()
            if connection.has_extn("auth"):
                connection.login(settings.smtp_user, settings.smtp_password.get_secret_value())
            else:
                logger.warning("El servidor SMTP no anuncia AUTH: s'envia sense autenticar")
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
