import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute, Match

from app.exceptions import TASK_TOKEN_INVALID, TaskTokenError
from app.routes import auth, categories, qualification, ranking, task, vote
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


# CORS permissiu per a desenvolupament local
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(task.router, prefix="/api", tags=["Task"])
app.include_router(vote.router, prefix="/api", tags=["Vote"])
app.include_router(ranking.router, prefix="/api", tags=["Ranking"])
app.include_router(auth.router, prefix="/api", tags=["Auth"])
app.include_router(categories.router, prefix="/api", tags=["Categories"])
app.include_router(qualification.router, prefix="/api", tags=["Qualification"])


@app.middleware("http")
async def telemetry_middleware(request: Request, call_next):
    matched_route = None
    for route in request.app.routes:
        if isinstance(route, APIRoute) and route.matches(request.scope)[0] == Match.FULL:
            matched_route = route.path
            break

    if matched_route is None:
        return await call_next(request)

    start = time.perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        duration = time.perf_counter() - start

        attrs = {
            "method": request.method,
            "route": matched_route,
            "status_code": status_code,
        }

        http_requests_total.add(1, attrs)
        http_requests_duration.record(duration, attrs)

        if status_code >= 500:
            http_errors_total.add(1, attrs)
