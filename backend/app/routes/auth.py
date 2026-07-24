from fastapi import APIRouter, Cookie, Response

from app.config import get_settings
from app.deps import CurrentUser, DbSession
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
    VerifyEmailRequest,
    VerifyEmailResponse,
)
from app.services import auth_service

router = APIRouter()


@router.post("/auth/register")
def register(payload: RegisterRequest, db: DbSession) -> RegisterResponse:
    """Alta d'usuari amb email, contrasenya i consentiment explícit."""
    return auth_service.register_user(db, payload)


@router.post("/auth/verify")
def verify(payload: VerifyEmailRequest, db: DbSession) -> VerifyEmailResponse:
    """Verificació de correu a partir d'un token signat."""
    return auth_service.verify_email(db, payload)


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
