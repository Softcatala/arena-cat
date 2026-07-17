import base64
import json

from app.security import (
    create_email_verification_token,
    create_task_token,
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
