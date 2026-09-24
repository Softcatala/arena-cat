from fastapi import APIRouter, Request

from app.deps import CurrentVerifiedUser, DbSession
from app.schemas import QualificationRequest, QualificationResponse, QualificationResult
from app.services import qualification_service

router = APIRouter()


@router.get("/qualification")
def get_qualification(current_user: CurrentVerifiedUser) -> QualificationResponse:
    """Retorna el qüestionari; l'esquema públic exclou les solucions i les explicacions."""
    return qualification_service.load_qualification()


@router.post("/qualification")
def submit_qualification(
    payload: QualificationRequest,
    request: Request,
    current_user: CurrentVerifiedUser,
    db: DbSession,
) -> QualificationResult:
    """Corregeix la prova i acredita l'usuari si assoleix el llindar del YAML."""
    return qualification_service.submit_qualification(
        db, current_user, payload, debug="debug" in request.query_params
    )
