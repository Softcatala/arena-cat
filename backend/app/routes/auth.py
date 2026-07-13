from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import RegisterRequest, RegisterResponse, VerifyEmailRequest, VerifyEmailResponse
from app.services import auth_service

router = APIRouter()


@router.post("/auth/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    """Alta d'usuari amb email, contrasenya i consentiment explícit."""
    return auth_service.register_user(db, payload)


@router.post("/auth/verify")
def verify(payload: VerifyEmailRequest, db: Session = Depends(get_db)) -> VerifyEmailResponse:
    """Verificació de correu a partir d'un token signat."""
    return auth_service.verify_email(db, payload)
