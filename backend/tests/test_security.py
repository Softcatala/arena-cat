import base64
import json

from app.security import create_token, verify_token


def test_verify_token():
    """Prova de verificar un token vàlid."""
    token = create_token(
        prompt_id=1, response_a_id=2, response_b_id=3, session_id="test_session_id"
    )
    payload = verify_token(token)

    # Comprovem que ha retornat els camps esperats i que existeix el camp exp.
    assert payload is not None
    assert payload["prompt_id"] == 1
    assert payload["response_a_id"] == 2
    assert payload["response_b_id"] == 3
    assert "exp" in payload


def test_verify_manipulated_payload():
    """Prova de verificar un token manipulat."""
    # Creem un token vàlid.
    token = create_token(
        prompt_id=1, response_a_id=2, response_b_id=3, session_id="test_session_id"
    )
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
    assert verify_token(token_alterat) is None
