from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy.orm import Session as OrmSession

from app.db import get_db
from app.rate_limit import rate_limit_auth
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


@router.post("/auth/register", dependencies=[Depends(rate_limit_auth)])
def register(payload: RegisterRequest, db: OrmSession = Depends(get_db)) -> RegisterResponse:
    """Alta d'usuari amb email, contrasenya i consentiment explícit."""
    return auth_service.register_user(db, payload)


@router.post("/auth/verify", dependencies=[Depends(rate_limit_auth)])
def verify(payload: VerifyEmailRequest, db: OrmSession = Depends(get_db)) -> VerifyEmailResponse:
    """Verificació de correu a partir d'un token signat."""
    return auth_service.verify_email(db, payload)


@router.post("/auth/login", dependencies=[Depends(rate_limit_auth)])
def login(
    payload: LoginRequest, response: Response, db: OrmSession = Depends(get_db)
) -> LoginResponse:
    """Autenticació d'usuari amb email i contrasenya. Retorna cookie de sessió."""
    _, raw_token = auth_service.login_user(db, payload)

    # Configura la cookie de sessió: HttpOnly, Secure (a producció), SameSite=Lax
    response.set_cookie(
        key="session_token",
        value=raw_token,
        httponly=True,
        secure=False,  # Cal posar-ho a True a producció amb HTTPS
        samesite="lax",
        max_age=86400,  # 24 hores
    )

    return LoginResponse(status="logged_in")


@router.post("/auth/logout")
def logout(
    response: Response,
    session_token: str | None = Cookie(None),
    db: OrmSession = Depends(get_db),
) -> LogoutResponse:
    """Tanca la sessió de l'usuari revocant el token."""
    if session_token is not None:
        payload = LogoutRequest(token=session_token)
        auth_service.logout_user(db, payload)

    # Esborra la cookie
    response.delete_cookie(key="session_token", samesite="lax")

    return LogoutResponse(status="logged_out")


@router.post("/auth/delete-account")
def delete_account(
    payload: DeleteAccountRequest,
    response: Response,
    session_token: str | None = Cookie(None),
    db: OrmSession = Depends(get_db),
) -> DeleteAccountResponse:
    """Dona de baixa el compte anonimitzant dades personals."""
    if session_token is None:
        raise HTTPException(status_code=401, detail="Sessió invàlida o caducada")

    result = auth_service.delete_account(db, payload, session_token)
    response.delete_cookie(key="session_token", samesite="lax")
    return result


@router.get("/auth/export")
def export_data(
    session_token: str | None = Cookie(None),
    db: OrmSession = Depends(get_db),
) -> ExportDataResponse:
    """Exporta les dades personals i els vots de l'usuari autenticat."""
    if session_token is None:
        raise HTTPException(status_code=401, detail="Sessió invàlida o caducada")

    return auth_service.export_user_data(db, session_token)
