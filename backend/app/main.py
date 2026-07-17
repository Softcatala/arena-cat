import logging

from fastapi import FastAPI

from app.routes import auth, ranking, task, vote

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI(title="arena-cat backend")

app.include_router(task.router, prefix="/api", tags=["Task"])
app.include_router(vote.router, prefix="/api", tags=["Vote"])
app.include_router(ranking.router, prefix="/api", tags=["Ranking"])
app.include_router(auth.router, prefix="/api", tags=["Auth"])
