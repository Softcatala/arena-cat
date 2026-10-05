"""Activitat diària: fus horari, límits del dia i persones úniques."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.models import EmailDelivery, Prompt, QualificationFailure, Response, Vote


def test_activity_requires_session(client):
    assert client.get("/api/activity").status_code == 401


def test_activity_defaults_to_today(client, logged_in_user):
    logged_in_user("activity@example.com")
    response = client.get("/api/activity")
    assert response.status_code == 200
    data = response.json()
    assert data["date"] == datetime.now(ZoneInfo("Europe/Madrid")).date().isoformat()
    assert data["registered_users"] == 1
    assert data["qualified_users"] == 1
    assert data["failed_users"] == data["votes"] == data["voters"] == 0
    assert data["verification_emails"] == data["password_reset_emails"] == 0
    assert datetime.fromisoformat(data["updated_at"]).tzinfo is not None


@pytest.mark.parametrize("day", ["2026-03-29", "2026-10-25"])
def test_activity_counts_local_day_and_unique_people(client, session, create_user, login, day):
    start = datetime.fromisoformat(day).replace(tzinfo=ZoneInfo("Europe/Madrid"))
    end = (start + timedelta(days=1)).astimezone(UTC)
    start = start.astimezone(UTC)
    first = create_user("first@example.com")
    second = create_user("second@example.com")
    first.created_at = start
    first.qualified_at = end - timedelta(microseconds=1)
    second.created_at = start - timedelta(microseconds=1)
    second.qualified_at = end
    prompt = Prompt(version="v1", code="activity", category_id=1, text="Text")
    session.add(prompt)
    session.flush()
    responses = [Response(prompt_id=prompt.id, model=model, text=model) for model in "abcd"]
    session.add_all(responses)
    session.flush()
    for index, instant in enumerate(
        [start - timedelta(microseconds=1), start, end - timedelta(microseconds=1), end]
    ):
        session.add(EmailDelivery(kind="verification", created_at=instant))
        session.add(QualificationFailure(user_id=first.id, created_at=instant))
        session.add(
            Vote(
                prompt_id=prompt.id,
                user_id=first.id,
                response_a_id=responses[index].id,
                response_b_id=responses[(index + 1) % 4].id,
                winner="tie",
                created_at=instant,
            )
        )
    session.add(EmailDelivery(kind="password_reset", created_at=start))
    session.commit()
    login(first.email)

    response = client.get(f"/api/activity?date={day}")
    assert response.status_code == 200
    data = response.json()
    assert data["date"] == day
    assert data["registered_users"] == data["qualified_users"] == 1
    assert data["failed_users"] == data["voters"] == 1
    assert data["votes"] == data["verification_emails"] == 2
    assert data["password_reset_emails"] == 1


def test_activity_empty_day_and_invalid_date(client, logged_in_user):
    logged_in_user("activity@example.com")
    data = client.get("/api/activity?date=2000-01-01").json()
    assert all(value == 0 for key, value in data.items() if key not in {"date", "updated_at"})
    assert client.get("/api/activity?date=invalid").status_code == 422
