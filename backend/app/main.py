import random

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Prompt, Response, Vote
from app.schemas import TaskResponse, VoteRequest, VoteResponse
from app.security import create_token, verify_token

app = FastAPI(title="arena-cat backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/task", response_model=TaskResponse)
def get_task(db: Session = Depends(get_db)):
    prompt = db.query(Prompt).order_by(func.random()).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="No hi ha prompts disponibles")

    responses = (
        db.query(Response)
        .filter(Response.prompt_id == prompt.id)
        .order_by(func.random())
        .limit(2)
        .all()
    )
    if len(responses) < 2:
        raise HTTPException(status_code=404, detail="No hi ha prou respostes per aquest prompt")

    random.shuffle(responses)
    resp_a, resp_b = responses[0], responses[1]

    token = create_token(prompt.id, resp_a.id, resp_b.id)

    return TaskResponse(
        prompt=prompt.text, response_a=resp_a.text, response_b=resp_b.text, token=token
    )


@app.post("/api/vote", response_model=VoteResponse)
def post_vote(vote_req: VoteRequest, db: Session = Depends(get_db)):
    payload = verify_token(vote_req.token)
    if not payload:
        raise HTTPException(status_code=401, detail="El token és invàlid o ha caducat")

    prompt_id = payload["prompt_id"]
    response_a_id = payload["response_a_id"]
    response_b_id = payload["response_b_id"]

    vote = Vote(
        prompt_id=prompt_id,
        response_a_id=response_a_id,
        response_b_id=response_b_id,
        winner=vote_req.winner,
    )

    db.add(vote)
    db.commit()

    return VoteResponse(status="ok")

@app.get("/api/ranking", response_model=list[dict])
def get_ranking(db: Session = Depends(get_db)):
    raise HTTPException(status_code=501, detail="No implementat")
    