import hmac
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession

from app.config import get_settings
from app.models import Session, User, Vote
from app.schemas import (
    DeleteAccountResponse,
    ExportDataResponse,
    ExportUserResponse,
    ExportVoteResponse,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    LogoutResponse,
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    ResetPasswordRequest,
    ResetPasswordResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
)
from app.security import (
    compute_email_hash,
    create_email_verification_token,
    create_password_reset_token,
    hash_password,
    hash_session_token,
    new_session_token,
    password_fingerprint,
    verify_email_verification_token,
    verify_password,
    verify_password_reset_token,
)


@dataclass(frozen=True)
class VerificationEmail:
    """Correu de verificació pendent d'enviar: l'adreça i el token de l'enllaç."""

    email: str
    token: str


@dataclass(frozen=True)
class PasswordResetEmail:
    """Correu de restabliment pendent d'enviar: l'adreça i el token de l'enllaç."""

    email: str
    token: str


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

    if (
        require_verified
        and get_settings().require_email_verification
        and user.email_verified_at is None
    ):
        raise HTTPException(status_code=403, detail="Cal verificar l'email per continuar")

    return user


def register_user(
    db: OrmSession, payload: RegisterRequest
) -> tuple[RegisterResponse, VerificationEmail | None]:
    """Registra un nou usuari.

    Si cal verificar el correu, retorna també el correu de verificació pendent d'enviar;
    l'enviament el fa qui crida, fora de la petició.
    """
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

    settings = get_settings()
    now = datetime.now(UTC)

    user = User(
        email=email,
        email_hash=email_hash,
        password_hash=password_hash,
        consent_version=settings.consent_version,
        consent_at=now,
        email_verified_at=None if settings.require_email_verification else now,
        verification_sent_at=now if settings.require_email_verification else None,
    )

    db.add(user)
    _commit(db, status_code=409, detail="No s'ha pogut completar el registre")

    db.refresh(user)

    if not settings.require_email_verification:
        return RegisterResponse(status="verified"), None

    verification_email = VerificationEmail(
        email=email, token=create_email_verification_token(user.id, email)
    )
    return (
        RegisterResponse(
            status="pending_verification",
            resend_cooldown_seconds=settings.verification_resend_cooldown_seconds,
        ),
        verification_email,
    )


def request_verification_resend(
    db: OrmSession, payload: ResendVerificationRequest
) -> VerificationEmail | None:
    """Prepara un nou correu de verificació si el compte hi té dret; si no, no fa res.

    Reserva el reenviament amb un únic UPDATE condicional: així dues peticions
    simultànies no poden saltar-se l'espera. El resultat no depèn de si l'adreça
    existeix, i qui crida respon igual en tots els casos.
    """
    settings = get_settings()
    if not settings.require_email_verification:
        return None

    now = datetime.now(UTC)
    cutoff = now - timedelta(seconds=settings.verification_resend_cooldown_seconds)
    claimed = db.execute(
        update(User)
        .where(
            User.email == payload.email.strip().lower(),
            User.deleted_at.is_(None),
            User.email_verified_at.is_(None),
            or_(User.verification_sent_at.is_(None), User.verification_sent_at <= cutoff),
        )
        .values(verification_sent_at=now)
        .returning(User.id, User.email)
    ).first()
    _commit(db)

    if claimed is None:
        return None
    return VerificationEmail(
        email=claimed.email, token=create_email_verification_token(claimed.id, claimed.email)
    )


def request_password_reset(
    db: OrmSession, payload: ForgotPasswordRequest
) -> PasswordResetEmail | None:
    """Prepara el correu de restabliment si el compte hi té dret; si no, no fa res.

    Reserva l'enviament amb un únic UPDATE condicional, com el reenviament de la
    verificació. Amb la verificació de correu exigida, només s'envia a comptes
    verificats: els altres han de demanar primer un reenviament de la verificació.
    El resultat no depèn de si l'adreça existeix, i qui crida respon igual sempre.
    """
    settings = get_settings()
    now = datetime.now(UTC)
    cutoff = now - timedelta(seconds=settings.password_reset_cooldown_seconds)
    conditions = [
        User.email == payload.email.strip().lower(),
        User.deleted_at.is_(None),
        or_(User.password_reset_sent_at.is_(None), User.password_reset_sent_at <= cutoff),
    ]
    if settings.require_email_verification:
        conditions.append(User.email_verified_at.is_not(None))

    claimed = db.execute(
        update(User)
        .where(*conditions)
        .values(password_reset_sent_at=now)
        .returning(User.id, User.email, User.password_hash)
    ).first()
    _commit(db)

    if claimed is None:
        return None
    return PasswordResetEmail(
        email=claimed.email,
        token=create_password_reset_token(claimed.id, claimed.password_hash),
    )


def reset_password(db: OrmSession, payload: ResetPasswordRequest) -> ResetPasswordResponse:
    """Canvia la contrasenya amb un token de restabliment i revoca totes les sessions.

    El token només serveix un cop: duu l'empremta de la contrasenya que substitueix, i
    el canvi es fa amb un UPDATE condicional a aquest hash, de manera que dues peticions
    simultànies amb el mateix enllaç no poden passar totes dues.
    """
    invalid = HTTPException(status_code=400, detail="Enllaç de restabliment invàlid o caducat")

    token_payload = verify_password_reset_token(payload.token)
    if not token_payload:
        raise invalid

    user = db.get(User, int(token_payload["user_id"]))
    if user is None or user.deleted_at is not None or user.password_hash is None:
        raise invalid
    if not hmac.compare_digest(
        str(token_payload.get("pwd", "")), password_fingerprint(user.password_hash)
    ):
        raise invalid

    changed = db.execute(
        update(User)
        .where(User.id == user.id, User.password_hash == user.password_hash)
        .values(password_hash=hash_password(payload.new_password))
        .returning(User.id)
    ).first()
    if changed is None:
        raise invalid

    # Qui tingui una sessió oberta amb la contrasenya antiga hi queda fora.
    db.execute(
        update(Session)
        .where(Session.user_id == user.id, Session.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    _commit(db)
    return ResetPasswordResponse()


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

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email o contrasenya incorrectes")

    # Després de la contrasenya: així només el propietari del compte veu que li cal verificar.
    if get_settings().require_email_verification and user.email_verified_at is None:
        raise HTTPException(
            status_code=403,
            detail="Email no verificat. Verifica el teu email primer.",
        )

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
    user.qualified_at = None
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
