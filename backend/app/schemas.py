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
