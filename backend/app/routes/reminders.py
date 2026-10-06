"""Preferències autenticades i baixa dels recordatoris sense sessió."""

from fastapi import APIRouter

from app.deps import CurrentUser, DbSession
from app.schemas import ReminderPreferences, ReminderUnsubscribe
from app.services import reminder_service

router = APIRouter()


@router.get("/auth/reminders")
def preferences(user: CurrentUser) -> ReminderPreferences:
    return ReminderPreferences(frequency=user.reminder_frequency)


@router.put("/auth/reminders")
def save_preferences(
    payload: ReminderPreferences, user: CurrentUser, db: DbSession
) -> ReminderPreferences:
    reminder_service.set_preferences(db, user, payload.frequency)
    return payload


@router.post("/auth/reminders/unsubscribe")
def unsubscribe(payload: ReminderUnsubscribe, db: DbSession) -> dict[str, str]:
    reminder_service.unsubscribe(db, payload.token)
    return {"status": "unsubscribed"}
