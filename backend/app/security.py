import base64
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import get_settings

_password_hasher = PasswordHasher()


def _sign_payload(payload: dict, secret: str) -> str:
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("utf-8").rstrip("=")
    signature = hmac.new(secret.encode("utf-8"), payload_bytes, "sha256").digest()
    signature_b64 = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
    return f"{payload_b64}.{signature_b64}"


def _verify_signed_payload(token: str, secret: str) -> dict | None:
    try:
        payload_b64, signature_b64 = token.split(".")

        payload_bytes = base64.urlsafe_b64decode(payload_b64 + "===")
        signature_provided = base64.urlsafe_b64decode(signature_b64 + "===")

        expected_signature = hmac.new(secret.encode("utf-8"), payload_bytes, "sha256").digest()

        if not hmac.compare_digest(expected_signature, signature_provided):
            return None

        payload = json.loads(payload_bytes.decode("utf-8"))
        if datetime.now(UTC).timestamp() > payload["exp"]:
            return None

        return payload
    except Exception:
        return None


def hash_password(password: str) -> str:
    """Calcula un hash Argon2id per a una contrasenya en text pla."""
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Comprova una contrasenya en text pla contra un hash Argon2id."""
    try:
        return _password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def compute_email_hash(email: str) -> str:
    """Retorna un hash HMAC-SHA256 de l'email normalitzat utilitzant pepper."""
    settings = get_settings()
    normalized = email.strip().lower().encode("utf-8")
    digest = hmac.new(settings.email_hash_pepper.encode("utf-8"), normalized, "sha256").hexdigest()
    return digest


def create_email_verification_token(user_id: int, email: str) -> str:
    """Crea un token temporal per verificar el correu d'un usuari."""
    settings = get_settings()
    exp = (datetime.now(UTC) + timedelta(hours=24)).timestamp()
    payload = {
        "user_id": str(user_id),
        "email": email.strip().lower(),
        "purpose": "email_verify",
        "exp": exp,
    }
    return _sign_payload(payload, settings.hmac_secret_key)


def verify_email_verification_token(token: str) -> dict | None:
    """Valida i retorna el payload d'un token de verificació de correu."""
    settings = get_settings()
    payload = _verify_signed_payload(token, settings.hmac_secret_key)
    if not payload:
        return None
    if payload.get("purpose") != "email_verify":
        return None
    return payload


def create_task_token(prompt_id: int, response_a_id: int, response_b_id: int, user_id: int) -> str:
    """Crea un token JWT per a una tasca donada.
    Args:
        prompt_id: identificador del prompt
        response_a_id: identificador de la resposta A
        response_b_id: identificador de la resposta B
        user_id: identificador de l'usuari

    Returns:
        str: token JWT
    """
    settings = get_settings()
    exp = (datetime.now(UTC) + timedelta(hours=1)).timestamp()

    payload = {
        "prompt_id": prompt_id,
        "response_a_id": response_a_id,
        "response_b_id": response_b_id,
        "user_id": user_id,
        "purpose": "task",
        "exp": exp,
    }
    return _sign_payload(payload, settings.hmac_secret_key)


def verify_task_token(token: str) -> dict | None:
    """
    Verifica un token de tasca HMAC i retorna el payload si és vàlid.

    A banda de la signatura i la caducitat, comprova que el token és realment un
    token de tasca (`purpose == "task"`) i que conté tots els camps obligatoris
    amb el tipus correcte. Així s'evita acceptar tokens signats amb un altre
    propòsit (p. ex. verificació de correu).

    Args:
        token: token HMAC a verificar
    Returns:
        dict | None: payload del token si és vàlid, None en cas contrari
    """
    settings = get_settings()
    payload = _verify_signed_payload(token, settings.hmac_secret_key)
    if not payload:
        return None
    if payload.get("purpose") != "task":
        return None
    required_int_fields = ("prompt_id", "response_a_id", "response_b_id", "user_id")
    for field in required_int_fields:
        if not isinstance(payload.get(field), int):
            return None
    return payload


def new_session_token() -> str:
    """Genera un token opac de sessió per al client."""
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """Hasheja un token de sessió per persistir-lo a base de dades."""
    settings = get_settings()
    return hmac.new(
        settings.session_secret.encode("utf-8"), token.encode("utf-8"), "sha256"
    ).hexdigest()
