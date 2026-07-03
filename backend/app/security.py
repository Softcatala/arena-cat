import base64
import hmac
import json
from datetime import UTC, datetime, timedelta

from app.config import get_settings


def create_token(prompt_id: int, response_a_id: int, response_b_id: int) -> str:
    settings = get_settings()
    exp = (datetime.now(UTC) + timedelta(hours=1)).timestamp()

    payload = {
        "prompt_id": prompt_id,
        "response_a_id": response_a_id,
        "response_b_id": response_b_id,
        "exp": exp,
    }

    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("utf-8").rstrip("=")

    signature = hmac.new(settings.api_secret_key.encode("utf-8"), payload_bytes, "sha256").digest()

    signature_b64 = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")

    return f"{payload_b64}.{signature_b64}"


def verify_token(token: str) -> dict | None:
    settings = get_settings()

    try:
        payload_b64, signature_b64 = token.split(".")

        payload_bytes = base64.urlsafe_b64decode(payload_b64 + "===")
        signature_provided = base64.urlsafe_b64decode(signature_b64 + "===")

        expected_signature = hmac.new(
            settings.api_secret_key.encode("utf-8"), payload_bytes, "sha256"
        ).digest()

        if not hmac.compare_digest(expected_signature, signature_provided):
            return None

        payload = json.loads(payload_bytes.decode("utf-8"))

        if datetime.now(UTC).timestamp() > payload["exp"]:
            return None

        return payload

    except Exception:
        return None
