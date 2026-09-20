from fastapi import APIRouter, BackgroundTasks, Cookie, Response

from app.config import get_settings
from app.deps import CurrentUser, DbSession, OptionalUser
from app.schemas import (
    DeleteAccountRequest,
    DeleteAccountResponse,
    ExportDataResponse,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    ResendVerificationResponse,
    SessionResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
)
from app.services import auth_service, email_service
from app.services.auth_service import VerificationEmail

router = APIRouter()


def _send_in_background(
    background_tasks: BackgroundTasks, verification_email: VerificationEmail | None
) -> None:
    """Programa l'enviament després de respondre, perquè SMTP no alenteixi la petició."""
    if verification_email is not None:
        background_tasks.add_task(
            email_service.send_verification_email,
            verification_email.email,
            verification_email.token,
        )


@router.post("/auth/register", response_model_exclude_none=True)
def register(
    payload: RegisterRequest, db: DbSession, background_tasks: BackgroundTasks
) -> RegisterResponse:
    """Alta d'usuari amb email, contrasenya i consentiment explícit."""
    response, verification_email = auth_service.register_user(db, payload)
    _send_in_background(background_tasks, verification_email)
    return response


@router.post("/auth/verify")
def verify(payload: VerifyEmailRequest, db: DbSession) -> VerifyEmailResponse:
    """Verificació de correu a partir d'un token signat."""
    return auth_service.verify_email(db, payload)


@router.post("/auth/resend-verification")
def resend_verification(
    payload: ResendVerificationRequest, db: DbSession, background_tasks: BackgroundTasks
) -> ResendVerificationResponse:
    """Reenvia el correu de verificació. Respon igual tant si el compte existeix com si no."""
    _send_in_background(background_tasks, auth_service.request_verification_resend(db, payload))
    return ResendVerificationResponse(
        resend_cooldown_seconds=get_settings().verification_resend_cooldown_seconds
    )


@router.post("/auth/login")
def login(payload: LoginRequest, response: Response, db: DbSession) -> LoginResponse:
    """Autenticació d'usuari amb email i contrasenya. Retorna cookie de sessió."""
    _, raw_token = auth_service.login_user(db, payload)

    settings = get_settings()
    response.set_cookie(
        key=settings.cookie_name,
        value=raw_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.cookie_max_age,
    )

    return LoginResponse(status="logged_in")


@router.get("/auth/session")
def get_session(current_user: OptionalUser) -> SessionResponse:
    """Indica si la cookie rebuda correspon a una sessió activa.

    El client ho consulta en carregar la pàgina per saber si ha de demanar les
    credencials. Respon 200 encara que no hi hagi sessió, de manera que un 401
    sempre vol dir que la sessió s'ha perdut i no que mai n'hi hagi hagut cap.
    """
    if current_user is None:
        return SessionResponse(authenticated=False)

    return SessionResponse(
        authenticated=True,
        email=current_user.email,
        email_verified=current_user.email_verified_at is not None,
        qualified=current_user.qualified_at is not None,
    )


@router.post("/auth/logout")
def logout(
    response: Response,
    db: DbSession,
    session_token: str | None = Cookie(default=None, alias=get_settings().cookie_name),
) -> LogoutResponse:
    """Tanca la sessió de l'usuari revocant el token."""
    if session_token is not None:
        auth_service.logout_user(db, LogoutRequest(token=session_token))

    response.delete_cookie(key=get_settings().cookie_name, samesite=get_settings().cookie_samesite)

    return LogoutResponse(status="logged_out")


@router.post("/auth/delete-account")
def delete_account(
    payload: DeleteAccountRequest,
    response: Response,
    current_user: CurrentUser,
    db: DbSession,
) -> DeleteAccountResponse:
    """Dona de baixa el compte anonimitzant dades personals."""
    result = auth_service.delete_account(db, current_user, payload.current_password)
    settings = get_settings()
    response.delete_cookie(key=settings.cookie_name, samesite=settings.cookie_samesite)
    return result


@router.get("/auth/export")
def export_data(current_user: CurrentUser, db: DbSession) -> ExportDataResponse:
    """Exporta les dades personals i els vots de l'usuari autenticat."""
    return auth_service.export_user_data(db, current_user)
