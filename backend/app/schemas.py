from pydantic import BaseModel

from app.models import Winner


class TaskResponse(BaseModel):
    prompt: str
    response_a: str
    response_b: str
    token: str


class VoteRequest(BaseModel):
    winner: Winner
    token: str


class VoteResponse(BaseModel):
    status: str = "ok"



class RegisterRequest(BaseModel):
    email: str
    password: str
    consent: bool


class RegisterResponse(BaseModel):
    status: str = "pending_verification"


class VerifyEmailRequest(BaseModel):
    token: str


class VerifyEmailResponse(BaseModel):
    status: str = "verified"


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    status: str = "logged_in"


class LogoutRequest(BaseModel):
    token: str


class LogoutResponse(BaseModel):
    status: str = "logged_out"


class DeleteAccountRequest(BaseModel):
    current_password: str


class DeleteAccountResponse(BaseModel):
    status: str = "deleted"


class ExportVoteResponse(BaseModel):
    id: int
    prompt_id: int
    response_a_id: int
    response_b_id: int
    winner: Winner
    session_id: str | None
    response_time_s: float | None
    created_at: str


class ExportUserResponse(BaseModel):
    id: int
    email: str | None
    email_verified_at: str | None
    consent_version: str
    consent_at: str | None
    created_at: str
    deleted_at: str | None


class ExportDataResponse(BaseModel):
    user: ExportUserResponse
    votes: list[ExportVoteResponse]

class PairwiseStat(BaseModel):
    model_a: str
    model_b: str
    wins_a: int
    wins_b: int
    ties: int
    neither: int
    win_rate_a: float | None

class RankingResponse(BaseModel):
    category_code: str
    n_votes_total: int
    n_votes_decisive: int
    n_ties: int
    n_neither: int
    models: list[str]
    best_model: str | None
    bt_skills: dict[str, float]
    raw_pairwise: list[PairwiseStat]
    cycle_detected: bool
    cycle_path: list[str]

