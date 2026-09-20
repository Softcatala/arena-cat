import base64
import json

from app import security
from app.security import (
    create_email_verification_token,
    create_password_reset_token,
    create_task_token,
    password_fingerprint,
    verify_email_verification_token,
    verify_password_reset_token,
    verify_task_token,
)


def test_verify_task_token():
    """Prova de verificar un token vàlid."""
    token = create_task_token(prompt_id=1, response_a_id=2, response_b_id=3, user_id=7)
    payload = verify_task_token(token)

    # Comprovem que ha retornat els camps esperats i que existeix el camp exp.
    assert payload is not None
    assert payload["prompt_id"] == 1
    assert payload["response_a_id"] == 2
    assert payload["response_b_id"] == 3
    assert payload["purpose"] == "task"
    assert "exp" in payload
    assert "vote_after" in payload


def test_verify_task_token_rejects_other_purpose():
    """Un token de verificació de correu no ha de passar com a token de tasca."""
    email_token = create_email_verification_token(user_id=7, email="user@example.com")

    # Tot i estar signat correctament, no té purpose="task".
    assert verify_task_token(email_token) is None


def test_verify_manipulated_payload():
    """Prova de verificar un token manipulat."""
    # Creem un token vàlid.
    token = create_task_token(prompt_id=1, response_a_id=2, response_b_id=3, user_id=7)
    payload_b64, signature_b64 = token.split(".")

    # Descodifiquem i alterem el payload.
    payload_bytes = base64.urlsafe_b64decode(payload_b64 + "===")
    payload = json.loads(payload_bytes.decode("utf-8"))
    payload["prompt_id"] = 123  # Hacker canviant l'ID

    # El tornem a codificar sense tocar la signatura original.
    payload_bytes_alterat = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64_alterat = (
        base64.urlsafe_b64encode(payload_bytes_alterat).decode("utf-8").rstrip("=")
    )

    token_alterat = f"{payload_b64_alterat}.{signature_b64}"

    # Comprovem que la funció detecta la manipulació i retorna None.
    assert verify_task_token(token_alterat) is None


def test_password_reset_token_round_trip():
    token = create_password_reset_token(user_id=7, password_hash="hash-actual")

    payload = verify_password_reset_token(token)

    assert payload is not None
    assert payload["user_id"] == "7"
    assert payload["purpose"] == "password_reset"
    assert payload["pwd"] == password_fingerprint("hash-actual")


def test_password_fingerprint_depends_on_the_hash_and_does_not_reveal_it():
    assert password_fingerprint("un-hash") == password_fingerprint("un-hash")
    assert password_fingerprint("un-hash") != password_fingerprint("altre-hash")
    assert "un-hash" not in password_fingerprint("un-hash")


def test_password_reset_and_email_verification_tokens_are_not_interchangeable():
    reset_token = create_password_reset_token(user_id=7, password_hash="hash")
    email_token = create_email_verification_token(user_id=7, email="user@example.com")

    assert verify_email_verification_token(reset_token) is None
    assert verify_password_reset_token(email_token) is None


def test_password_reset_token_rejects_a_tampered_token():
    token = create_password_reset_token(user_id=7, password_hash="hash")

    assert verify_password_reset_token(token + "x") is None
    assert verify_password_reset_token("no.token") is None


def test_password_reset_token_rejects_an_expired_token(monkeypatch):
    monkeypatch.setattr(security, "PASSWORD_RESET_TTL_MINUTES", -1)
    token = create_password_reset_token(user_id=7, password_hash="hash")

    assert verify_password_reset_token(token) is None
