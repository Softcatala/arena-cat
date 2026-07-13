import logging
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import User
from app.schemas import RegisterRequest, RegisterResponse, VerifyEmailRequest, VerifyEmailResponse
from app.security import (
    compute_email_hash,
    create_email_verification_token,
    hash_password,
    verify_email_verification_token,
)

logger = logging.getLogger(__name__)


def register_user(db: Session, payload: RegisterRequest) -> RegisterResponse:
    """Registra un nou usuari i genera token de verificació de correu."""
    if not payload.consent:
        raise HTTPException(status_code=400, detail="Cal acceptar el consentiment explícit")

    email = payload.email.strip().lower()
    email_hash = compute_email_hash(email)

    existing = db.scalar(select(User).where(User.email_hash == email_hash))
    if existing is not None:
        if existing.deleted_at is not None:
            raise HTTPException(status_code=409, detail="Aquest correu ja s'havia registrat")
        raise HTTPException(status_code=409, detail="Aquest correu ja està registrat")

    password_hash = hash_password(payload.password)

    user = User(
        email=email,
        email_hash=email_hash,
        password_hash=password_hash,
        consent_version=get_settings().consent_version,
        consent_at=datetime.now(UTC),
    )

    db.add(user)
    try:
        db.commit()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(status_code=409, detail="No s'ha pogut completar el registre") from err

    db.refresh(user)

    verification_token = create_email_verification_token(user.id, email)
    # v1: no hi ha servei d'email; deixem el token al log perquè es pugui provar el flux.
    logger.info("Email verification token for %s: %s", email, verification_token)

    return RegisterResponse(status="pending_verification")


def verify_email(db: Session, payload: VerifyEmailRequest) -> VerifyEmailResponse:
    """Valida el token de verificació i marca el correu com a verificat."""
    token_payload = verify_email_verification_token(payload.token)
    if not token_payload:
        raise HTTPException(status_code=400, detail="Token de verificació invàlid o caducat")

    user_id = int(token_payload["user_id"])
    email = token_payload["email"]

    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Usuari no trobat")

    if user.email != email:
        raise HTTPException(status_code=400, detail="Token de verificació invàlid")

    if user.email_verified_at is None:
        user.email_verified_at = datetime.now(UTC)
        db.add(user)
        db.commit()

    return VerifyEmailResponse(status="verified")
