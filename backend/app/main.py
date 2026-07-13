from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import auth, ranking, task, vote

app = FastAPI(title="arena-cat backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(task.router, prefix="/api", tags=["Task"])
app.include_router(vote.router, prefix="/api", tags=["Vote"])
app.include_router(ranking.router, prefix="/api", tags=["Ranking"])
app.include_router(auth.router, prefix="/api", tags=["Auth"])
