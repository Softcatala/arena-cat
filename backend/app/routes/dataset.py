from secrets import compare_digest
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Response as HttpResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from app.config import get_settings
from app.deps import DbSession
from app.models import Category, Prompt, Response
from app.schemas import DatasetResponse

router = APIRouter()


@router.get("/dataset")
def get_dataset(
    db: DbSession,
    response: HttpResponse,
    token: Annotated[HTTPAuthorizationCredentials | None, Depends(HTTPBearer(auto_error=False))],
) -> DatasetResponse:
    """Retorna totes les categories, revisions de prompts i respostes carregades."""
    expected = get_settings().admin_api_token.get_secret_value()
    if (
        not expected
        or token is None
        or not compare_digest(token.credentials.encode(), expected.encode())
    ):
        raise HTTPException(
            status_code=401, detail="Token no vàlid", headers={"WWW-Authenticate": "Bearer"}
        )
    response.headers["Cache-Control"] = "no-store"
    return DatasetResponse(
        categories=db.scalars(select(Category).order_by(Category.id)).all(),
        prompts=db.scalars(select(Prompt).order_by(Prompt.id)).all(),
        responses=db.scalars(select(Response).order_by(Response.id)).all(),
    )
