import logging
import time
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.exceptions import TASK_TOKEN_INVALID, TaskTokenError
from app.routes import (
    activity,
    admin,
    auth,
    categories,
    dataset,
    qualification,
    ranking,
    task,
    vote,
)
from app.telemetry.metrics import http_errors_total, http_requests_duration, http_requests_total

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI(title="arena-cat backend")


@app.exception_handler(TaskTokenError)
async def task_token_error_handler(_request: Request, exc: TaskTokenError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_code": TASK_TOKEN_INVALID},
    )


# Només els orígens configurats poden llegir respostes amb credencials.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@app.middleware("http")
async def origin_middleware(request: Request, call_next):
    """Refusa les escriptures que un navegador envia des d'un origen no autoritzat.

    CORS només impedeix llegir la resposta: la petició s'executa igualment. Un navegador
    envia sempre `Origin` en una petició d'un altre origen, així que n'hi ha prou amb
    comprovar-lo. S'accepta si és un origen configurat o el mateix de l'API (el proxy del
    frontend en desenvolupament). Sense `Origin` (curl, scripts) no és una petició de navegador.
    """
    origin = request.headers.get("origin")
    if origin is not None and request.method not in SAFE_METHODS:
        host = urlsplit(origin).netloc
        same_origin = bool(host) and host == request.headers.get("host")
        if origin not in get_settings().allowed_origins and not same_origin:
            return JSONResponse(status_code=403, content={"detail": "Origen no permès."})
    return await call_next(request)


app.include_router(task.router, prefix="/api", tags=["Task"])
app.include_router(vote.router, prefix="/api", tags=["Vote"])
app.include_router(ranking.router, prefix="/api", tags=["Ranking"])
app.include_router(auth.router, prefix="/api", tags=["Auth"])
app.include_router(categories.router, prefix="/api", tags=["Categories"])
app.include_router(dataset.router, prefix="/api", tags=["Dataset"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(activity.router, prefix="/api", tags=["Activity"])
app.include_router(qualification.router, prefix="/api", tags=["Qualification"])


API_PREFIX = "/api"


@app.middleware("http")
async def telemetry_middleware(request: Request, call_next):
    start = time.perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        route = request.scope.get("route")
        if route is not None:
            duration = time.perf_counter() - start
            attrs = {
                "method": request.method,
                "route": f"{API_PREFIX}{route.path}",
                "status_code": status_code,
            }

            http_requests_total.add(1, attrs)
            http_requests_duration.record(duration, attrs)

            if status_code >= 500:
                http_errors_total.add(1, attrs)
