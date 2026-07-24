from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

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
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    consent: bool


class RegisterResponse(BaseModel):
    status: str = "pending_verification"


class VerifyEmailRequest(BaseModel):
    token: str


class VerifyEmailResponse(BaseModel):
    status: str = "verified"


class LoginRequest(BaseModel):
    email: EmailStr
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
    model_config = ConfigDict(from_attributes=True)

    id: int
    prompt_id: int
    response_a_id: int
    response_b_id: int
    winner: Winner
    session_id: str | None
    response_time_s: float | None
    created_at: datetime


class ExportUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str | None
    email_verified_at: datetime | None
    consent_version: str
    consent_at: datetime | None
    created_at: datetime
    deleted_at: datetime | None


class ExportDataResponse(BaseModel):
    user: ExportUserResponse
    votes: list[ExportVoteResponse]
