"""Recomptes diaris d'activitat de la plataforma a partir de PostgreSQL."""

from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query, Response
from sqlalchemy import distinct, func, select

from app.deps import CurrentUser, DbSession
from app.models import EmailDelivery, QualificationFailure, User, Vote
from app.schemas import ActivityResponse

router = APIRouter()
LOCAL_TIMEZONE = ZoneInfo("Europe/Madrid")


@router.get("/activity")
def get_activity(
    db: DbSession,
    current_user: CurrentUser,
    response: Response,
    day: Annotated[date | None, Query(alias="date", le=date(9999, 12, 30))] = None,
) -> ActivityResponse:
    """Compta esdeveniments del dia local, amb el límit superior exclòs."""
    now = datetime.now(UTC)
    day = day or now.astimezone(LOCAL_TIMEZONE).date()
    start = datetime.combine(day, time.min, LOCAL_TIMEZONE).astimezone(UTC)
    end = datetime.combine(day + timedelta(days=1), time.min, LOCAL_TIMEZONE).astimezone(UTC)

    def count(column, timestamp, *conditions):
        return (
            select(func.count(column))
            .where(timestamp >= start, timestamp < end, *conditions)
            .scalar_subquery()
        )

    counts = (
        db.execute(
            select(
                count(User.id, User.created_at).label("registered_users"),
                count(User.id, User.qualified_at).label("qualified_users"),
                count(
                    distinct(QualificationFailure.user_id), QualificationFailure.created_at
                ).label("failed_users"),
                count(
                    EmailDelivery.id, EmailDelivery.created_at, EmailDelivery.kind == "verification"
                ).label("verification_emails"),
                count(
                    EmailDelivery.id,
                    EmailDelivery.created_at,
                    EmailDelivery.kind == "password_reset",
                ).label("password_reset_emails"),
                count(distinct(Vote.user_id), Vote.created_at).label("voters"),
                count(Vote.id, Vote.created_at).label("votes"),
            )
        )
        .mappings()
        .one()
    )
    response.headers["Cache-Control"] = "no-store"
    return ActivityResponse(date=day, updated_at=now, **counts)
