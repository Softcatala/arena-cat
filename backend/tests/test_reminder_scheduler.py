"""Programació setmanal en hora local, inclosos els canvis d'horari."""

from datetime import UTC, datetime

from app.services.reminder_scheduler import next_run


def test_next_run_before_monday_morning():
    assert next_run(datetime(2026, 10, 5, 7, 59, tzinfo=UTC)) == datetime(
        2026, 10, 5, 8, tzinfo=UTC
    )


def test_next_run_after_monday_morning():
    assert next_run(datetime(2026, 10, 5, 8, tzinfo=UTC)) == datetime(2026, 10, 12, 8, tzinfo=UTC)


def test_next_run_changes_utc_hour_after_daylight_saving():
    assert next_run(datetime(2026, 3, 23, 9, tzinfo=UTC)) == datetime(2026, 3, 30, 8, tzinfo=UTC)
    assert next_run(datetime(2026, 10, 19, 8, tzinfo=UTC)) == datetime(2026, 10, 26, 9, tzinfo=UTC)
