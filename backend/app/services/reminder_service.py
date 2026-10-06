"""Recordatoris voluntaris després d'un període sense votar."""

import logging
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import quote
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_sessionmaker
from app.models import User, Vote
from app.services import email_service
from app.services.task_service import get_task_progress_for_user

logger = logging.getLogger(__name__)
REMINDER_INTERVAL = timedelta(days=7)
REMINDER_TIMEZONE = ZoneInfo("Europe/Madrid")


def set_preferences(db: Session, user: User, enabled: bool, now: datetime | None = None) -> None:
    """Desa la tria explícita; una subscripció nova renova el token de baixa."""
    user = db.scalar(
        select(User)
        .where(User.id == user.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if enabled != user.reminder_enabled:
        user.reminder_enabled = enabled
        user.reminder_count = 0
        if enabled:
            user.reminder_consent_at = now or datetime.now(UTC)
            user.reminder_token = secrets.token_urlsafe(32)
    db.commit()


def unsubscribe(db: Session, token: str) -> None:
    """Baixa idempotent sense sessió; no revela si el token existeix."""
    user = db.scalar(select(User).where(User.reminder_token == token).with_for_update())
    if user is not None:
        user.reminder_enabled = False
        db.commit()


def send_due_reminders(db: Session, now: datetime | None = None) -> int:
    """Envia els recordatoris pendents amb bloqueig per evitar execucions simultànies."""
    now = now or datetime.now(UTC)
    sent = 0
    ids = db.scalars(select(User.id).where(User.reminder_enabled.is_(True))).all()
    for user_id in ids:
        user = db.scalar(
            select(User)
            .where(User.id == user_id)
            .with_for_update(skip_locked=True)
            .execution_options(populate_existing=True)
        )
        if user is None:
            db.rollback()
            continue
        if (
            not user.reminder_enabled
            or user.deleted_at is not None
            or user.email_verified_at is None
            or user.qualified_at is None
        ):
            db.rollback()
            continue
        last_vote, votes = db.execute(
            select(func.max(Vote.created_at), func.count(Vote.id)).where(Vote.user_id == user.id)
        ).one()
        if last_vote is None:
            db.rollback()
            continue
        count = 0 if user.reminder_vote_at != last_vote else user.reminder_count
        baseline = max(last_vote, user.reminder_consent_at, user.reminder_sent_at or last_vote)
        if (
            count >= 3
            or now.astimezone(REMINDER_TIMEZONE) - baseline.astimezone(REMINDER_TIMEZONE)
            < REMINDER_INTERVAL
            or not get_task_progress_for_user(user, db).remaining
        ):
            db.rollback()
            continue
        base = get_settings().frontend_base_url.rstrip("/")
        link = f"{base}/reminders/unsubscribe?token={quote(user.reminder_token, safe='')}"
        message = email_service.build_reminder_message(user.email, votes, base, link)
        try:
            accepted = email_service.send_email(message)
        except OSError as error:
            logger.error("No s’ha pogut enviar el recordatori: %s", type(error).__name__)
            accepted = False
        if accepted:
            user.reminder_sent_at = now
            user.reminder_vote_at = last_vote
            user.reminder_count = count + 1
            db.commit()
            sent += 1
        else:
            db.rollback()
    return sent


def main() -> None:
    """Punt d'entrada per a l'execució setmanal des del planificador."""
    if not get_settings().smtp_host:
        raise SystemExit("Cal configurar SMTP_HOST per enviar recordatoris.")
    with get_sessionmaker()() as db:
        print(f"Recordatoris enviats: {send_due_reminders(db)}")


if __name__ == "__main__":
    main()
