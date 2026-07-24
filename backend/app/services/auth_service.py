import logging
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession

from app.config import get_settings
from app.models import Session, User, Vote
from app.schemas import (
    DeleteAccountResponse,
    ExportDataResponse,
    ExportUserResponse,
    ExportVoteResponse,
    LoginRequest,
    LogoutRequest,
    LogoutResponse,
    RegisterRequest,
    RegisterResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
)
from app.security import (
    compute_email_hash,
    create_email_verification_token,
    hash_password,
    hash_session_token,
    new_session_token,
    verify_email_verification_token,
    verify_password,
)

logger = logging.getLogger(__name__)


def _commit(db: OrmSession, *, status_code: int = 500, detail: str = "Error intern") -> None:
    """Fa commit de la transacció i, si falla per integritat, la desfà i llança HTTP."""
    try:
        db.commit()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(status_code=status_code, detail=detail) from err


def resolve_session_user(
    db: OrmSession, session_token: str | None, *, require_verified: bool = False
) -> User:
    """Resol la sessió activa d'una cookie i en retorna l'usuari.

    Comprova que el token existeix, que la sessió no està revocada ni caducada i
    que l'usuari existeix i no està donat de baixa. Amb `require_verified`, exigeix
    a més que l'email estigui verificat.

    Args:
        db: sessió SQLAlchemy.
        session_token: token de sessió en clar rebut a la cookie (pot ser None).
        require_verified: si és cert, exigeix email verificat (403 altrament).

    Returns:
        User: l'usuari propietari de la sessió activa.
    """
    if session_token is None:
        raise HTTPException(status_code=401, detail="Sessió invàlida o caducada")

    token_hash = hash_session_token(session_token)
    now = datetime.now(UTC)

    active_session = db.scalar(
        select(Session).where(
            Session.token_hash == token_hash,
            Session.revoked_at.is_(None),
            Session.expires_at > now,
        )
    )
    if active_session is None:
        raise HTTPException(status_code=401, detail="Sessió invàlida o caducada")

    user = db.get(User, active_session.user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(status_code=401, detail="Sessió invàlida o caducada")

    if require_verified and user.email_verified_at is None:
        raise HTTPException(status_code=403, detail="Cal verificar l'email per continuar")

    return user


def register_user(db: OrmSession, payload: RegisterRequest) -> RegisterResponse:
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
    _commit(db, status_code=409, detail="No s'ha pogut completar el registre")

    db.refresh(user)

    verification_token = create_email_verification_token(user.id, email)
    # v1: no hi ha servei d'email; deixem el token al log perquè es pugui provar el flux.
    logger.info("Email verification token for %s: %s", email, verification_token)

    return RegisterResponse(status="pending_verification")


def verify_email(db: OrmSession, payload: VerifyEmailRequest) -> VerifyEmailResponse:
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
        _commit(db)

    return VerifyEmailResponse(status="verified")


def login_user(db: OrmSession, payload: LoginRequest) -> tuple[User, str]:
    """Autentica l'usuari, crea una sessió i retorna l'usuari i el token en clar."""
    email = payload.email.strip().lower()

    user = db.scalar(select(User).where(User.email == email))
    if user is None or user.deleted_at is not None:
        raise HTTPException(status_code=401, detail="Email o contrasenya incorrectes")

    if user.email_verified_at is None:
        raise HTTPException(
            status_code=403,
            detail="Email no verificat. Verifica el teu email primer.",
        )

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email o contrasenya incorrectes")

    # Crea la sessió
    raw_token = new_session_token()
    token_hash = hash_session_token(raw_token)
    ttl_hours = get_settings().session_ttl_hours
    expires_at = datetime.now(UTC) + timedelta(hours=ttl_hours)

    session = Session(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )

    db.add(session)
    _commit(db, detail="No s'ha pogut crear la sessió")

    return user, raw_token


def logout_user(db: OrmSession, payload: LogoutRequest) -> LogoutResponse:
    """Revoca la sessió de l'usuari."""
    token_hash = hash_session_token(payload.token)
    session = db.scalar(select(Session).where(Session.token_hash == token_hash))
    if session is not None:
        session.revoked_at = datetime.now(UTC)
        db.add(session)
        _commit(db)

    return LogoutResponse(status="logged_out")


def anonymize_user_rgpd(user: User, now: datetime) -> None:
    """Anonimitza les dades personals de l'usuari mantenint claus tècniques."""
    user.email = None
    user.password_hash = None
    user.email_verified_at = None
    user.consent_at = None
    user.deleted_at = now


def delete_account(
    db: OrmSession,
    user: User,
    current_password: str,
) -> DeleteAccountResponse:
    """Dona de baixa el compte anonimitzant dades personals i revocant sessions."""
    now = datetime.now(UTC)

    if not verify_password(current_password, user.password_hash):
        raise HTTPException(status_code=401, detail="Contrasenya incorrecta")

    # Anonimització RGPD: preservem user.id i email_hash per evitar re-registres.
    anonymize_user_rgpd(user, now)
    db.add(user)

    user_sessions = db.scalars(
        select(Session).where(
            Session.user_id == user.id,
            Session.revoked_at.is_(None),
        )
    ).all()
    for session in user_sessions:
        session.revoked_at = now
        db.add(session)

    _commit(db)
    return DeleteAccountResponse(status="deleted")


def export_user_data(db: OrmSession, user: User) -> ExportDataResponse:
    """Exporta les dades personals i els vots de l'usuari autenticat."""
    votes = db.scalars(
        select(Vote).where(Vote.user_id == user.id).order_by(Vote.created_at.asc())
    ).all()

    return ExportDataResponse(
        user=ExportUserResponse.model_validate(user),
        votes=[ExportVoteResponse.model_validate(vote) for vote in votes],
    )
