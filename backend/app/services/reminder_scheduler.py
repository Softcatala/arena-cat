"""Procés del contenidor de recordatoris: cada dilluns a les 10 h de Barcelona."""

import logging
import signal
from datetime import UTC, datetime, timedelta
from threading import Event

from app.config import get_settings
from app.services import reminder_service

logger = logging.getLogger(__name__)
TIMEZONE = reminder_service.REMINDER_TIMEZONE


def next_run(now: datetime) -> datetime:
    """Calcula el proper dilluns a les 10 h, conservant l'hora local a l'estiu."""
    local = now.astimezone(TIMEZONE)
    scheduled = local.replace(hour=10, minute=0, second=0, microsecond=0)
    scheduled += timedelta(days=(7 - local.weekday()) % 7)
    if scheduled <= local:
        scheduled += timedelta(days=7)
    return scheduled.astimezone(UTC)


def main() -> None:
    """Espera la propera execució i s'atura quan Docker envia SIGTERM."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    stopped = Event()
    signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    signal.signal(signal.SIGINT, lambda *_: stopped.set())
    while not stopped.is_set():
        scheduled = next_run(datetime.now(UTC))
        logger.info("Proper enviament: %s", scheduled.astimezone(TIMEZONE).isoformat())
        while not stopped.is_set():
            seconds = (scheduled - datetime.now(UTC)).total_seconds()
            if seconds <= 0:
                break
            stopped.wait(min(seconds, 60))
        if stopped.is_set():
            break
        if not get_settings().smtp_host:
            logger.warning("SMTP_HOST no configurat; s'omet l'enviament setmanal")
            continue
        try:
            reminder_service.main()
        except Exception as error:
            # El text dels errors de connexió pot contenir dades personals o credencials.
            logger.error("Ha fallat l'enviament setmanal: %s", type(error).__name__)


if __name__ == "__main__":
    main()
