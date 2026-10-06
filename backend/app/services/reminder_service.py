"""Recordatoris voluntaris després d'un període sense votar."""

import argparse
import logging
import secrets
import signal
from datetime import UTC, datetime, timedelta
from threading import Event
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


def claim_invitation(db: Session, user: User, now: datetime | None = None) -> bool:
    """Reserva una invitació cada deu vots, com a màxim un cop cada trenta dies."""
    now = now or datetime.now(UTC)
    user = db.scalar(
        select(User)
        .where(User.id == user.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    count, last_vote = db.execute(
        select(func.count(Vote.id), func.max(Vote.created_at)).where(Vote.user_id == user.id)
    ).one()
    previous = user.reminder_invited_at
    if (
        user.reminder_enabled
        or not count
        or count % 10
        or (previous is not None and (now - previous < timedelta(days=30) or last_vote <= previous))
    ):
        db.rollback()
        return False
    user.reminder_invited_at = now
    db.commit()
    return True


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
        count = (
            user.reminder_count
            if user.reminder_sent_at and last_vote <= user.reminder_sent_at
            else 0
        )
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
            user.reminder_count = count + 1
            db.commit()
            sent += 1
        else:
            db.rollback()
    return sent


def next_run(now: datetime) -> datetime:
    """Calcula el proper dilluns a les 10 h, conservant l'hora local a l'estiu."""
    local = now.astimezone(REMINDER_TIMEZONE)
    scheduled = local.replace(hour=10, minute=0, second=0, microsecond=0)
    scheduled += timedelta(days=(7 - local.weekday()) % 7)
    if scheduled <= local:
        scheduled += REMINDER_INTERVAL
    return scheduled.astimezone(UTC)


def run_once() -> None:
    """Envia els correus pendents amb la configuració del desplegament."""
    if not get_settings().smtp_host:
        logger.warning("SMTP_HOST no configurat; s'omet l'enviament")
        return
    with get_sessionmaker()() as db:
        logger.info("Recordatoris enviats: %s", send_due_reminders(db))


def main() -> None:
    """Executa un enviament o el planificador setmanal del contenidor."""
    parser = argparse.ArgumentParser(description="Recordatoris setmanals d'Arena Cat")
    parser.add_argument("--schedule", action="store_true", help="Programa cada dilluns a les 10 h")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if not parser.parse_args().schedule:
        run_once()
        return
    stopped = Event()
    signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    signal.signal(signal.SIGINT, lambda *_: stopped.set())
    while not stopped.is_set():
        scheduled = next_run(datetime.now(UTC))
        logger.info("Proper enviament: %s", scheduled.astimezone(REMINDER_TIMEZONE).isoformat())
        while not stopped.is_set():
            seconds = (scheduled - datetime.now(UTC)).total_seconds()
            if seconds <= 0:
                break
            stopped.wait(min(seconds, 60))
        if stopped.is_set():
            break
        try:
            run_once()
        except Exception as error:
            # El text dels errors de connexió pot contenir dades personals o credencials.
            logger.error("Ha fallat l'enviament setmanal: %s", type(error).__name__)


if __name__ == "__main__":
    main()
