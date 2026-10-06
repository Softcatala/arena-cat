"""Proves dels recordatoris voluntaris i dels límits d'enviament."""

from datetime import UTC, datetime, timedelta

import pytest

from app.models import Category, EmailDelivery, Prompt, Response, Vote, Winner
from app.services import reminder_service


def test_preferences_require_session(client):
    assert client.get("/api/auth/reminders").status_code == 401


def test_opt_in_and_unsubscribe(client, logged_in_user, session):
    user = logged_in_user("reminder@example.cat")
    assert client.get("/api/auth/reminders").json() == {"enabled": False}
    assert client.put("/api/auth/reminders", json={"enabled": True}).status_code == 200
    session.refresh(user)
    token = user.reminder_token
    assert user.reminder_consent_at is not None
    assert client.put("/api/auth/reminders", json={"enabled": "daily"}).status_code == 422
    client.post("/api/auth/logout")
    assert client.post("/api/auth/reminders/unsubscribe", json={"token": token}).status_code == 200
    session.refresh(user)
    assert user.reminder_enabled is False
    assert client.post("/api/auth/reminders/unsubscribe", json={"token": token}).status_code == 200


def seed_vote(session, user, now):
    category = session.query(Category).first()
    prompt = Prompt(code="reminder_1", version="v1", category_id=category.id, text="Text")
    session.add(prompt)
    session.flush()
    responses = [Response(prompt_id=prompt.id, model=str(i), text="Resposta") for i in range(3)]
    session.add_all(responses)
    session.flush()
    vote = Vote(
        user_id=user.id,
        prompt_id=prompt.id,
        response_a_id=responses[0].id,
        response_b_id=responses[1].id,
        winner=Winner.a,
        created_at=now - timedelta(days=8),
    )
    session.add(vote)
    session.commit()
    return vote


def test_send_cooldown_pause_and_resume(session, create_user, monkeypatch):
    now = datetime.now(UTC)
    user = create_user("send@example.cat")
    reminder_service.set_preferences(session, user, True, now - timedelta(days=9))
    vote = seed_vote(session, user, now)
    messages = []
    monkeypatch.setattr(
        reminder_service.email_service, "send_email", lambda m: messages.append(m) or True
    )
    assert reminder_service.send_due_reminders(session, now) == 1
    assert reminder_service.send_due_reminders(session, now) == 0
    assert reminder_service.send_due_reminders(session, now + timedelta(days=7)) == 1
    assert reminder_service.send_due_reminders(session, now + timedelta(days=14)) == 1
    assert reminder_service.send_due_reminders(session, now + timedelta(days=21)) == 0
    vote.created_at = now + timedelta(days=22)
    session.commit()
    assert reminder_service.send_due_reminders(session, now + timedelta(days=30)) == 1
    assert "List-Unsubscribe" in messages[0]
    assert session.query(EmailDelivery).filter_by(kind="reminder").count() == 4


def test_no_votes_or_unverified_users_are_not_sent(session, create_user, monkeypatch):
    now = datetime.now(UTC)
    user = create_user("empty@example.cat")
    reminder_service.set_preferences(session, user, True, now - timedelta(days=9))
    monkeypatch.setattr(reminder_service.email_service, "send_email", lambda m: True)
    assert reminder_service.send_due_reminders(session, now) == 0
    seed_vote(session, user, now)
    user.email_verified_at = None
    session.commit()
    assert reminder_service.send_due_reminders(session, now) == 0


def test_smtp_failure_does_not_consume_reminder(session, create_user, monkeypatch):
    now = datetime.now(UTC)
    user = create_user("failed@example.cat")
    reminder_service.set_preferences(session, user, True, now - timedelta(days=9))
    seed_vote(session, user, now)

    def fail(message):
        raise OSError("SMTP unavailable")

    monkeypatch.setattr(reminder_service.email_service, "send_email", fail)
    assert reminder_service.send_due_reminders(session, now) == 0
    assert user.reminder_sent_at is None
    assert user.reminder_count == 0
    assert session.query(EmailDelivery).filter_by(kind="reminder").count() == 0


def test_weekly_and_exhausted_tasks(session, create_user, monkeypatch):
    now = datetime.now(UTC)
    user = create_user("exhausted@example.cat")
    reminder_service.set_preferences(session, user, True, now - timedelta(days=8))
    vote = seed_vote(session, user, now)
    vote.created_at = now - timedelta(days=8)
    session.commit()
    monkeypatch.setattr(reminder_service.email_service, "send_email", lambda m: True)
    assert reminder_service.send_due_reminders(session, now - timedelta(days=2)) == 0
    assert reminder_service.send_due_reminders(session, now) == 1
    from app.models import TaskSkip

    responses = session.query(Response).order_by(Response.id).all()
    session.add_all(
        [
            TaskSkip(
                user_id=user.id,
                prompt_id=vote.prompt_id,
                response_a_id=responses[i].id,
                response_b_id=responses[2].id,
            )
            for i in (0, 1)
        ]
    )
    session.commit()
    assert reminder_service.send_due_reminders(session, now + timedelta(days=8)) == 0


def test_resubscribe_invalidates_old_token(client, logged_in_user, session):
    user = logged_in_user("tokens@example.cat")
    client.put("/api/auth/reminders", json={"enabled": True})
    session.refresh(user)
    old_token = user.reminder_token
    client.put("/api/auth/reminders", json={"enabled": False})
    client.put("/api/auth/reminders", json={"enabled": True})
    client.post("/api/auth/reminders/unsubscribe", json={"token": old_token})
    session.refresh(user)
    assert user.reminder_enabled is True
    assert user.reminder_token != old_token


def test_account_deletion_clears_preferences(client, logged_in_user, session):
    from conftest import DEFAULT_PASSWORD

    user = logged_in_user("delete-reminders@example.cat")
    client.put("/api/auth/reminders", json={"enabled": True})
    exported = client.get("/api/auth/export").json()["user"]
    assert exported["reminder_enabled"] is True
    assert exported["reminder_consent_at"] is not None
    assert "reminder_token" not in exported
    assert (
        client.post(
            "/api/auth/delete-account", json={"current_password": DEFAULT_PASSWORD}
        ).status_code
        == 200
    )
    session.refresh(user)
    assert user.reminder_enabled is False
    assert user.reminder_token is None
    assert user.reminder_consent_at is None


def test_weekly_send_keeps_local_time_after_daylight_saving(session, create_user, monkeypatch):
    previous_monday = datetime(2026, 3, 23, 9, tzinfo=UTC)
    user = create_user("summer@example.cat")
    reminder_service.set_preferences(session, user, True, previous_monday - timedelta(days=9))
    seed_vote(session, user, previous_monday)
    monkeypatch.setattr(reminder_service.email_service, "send_email", lambda m: True)
    assert reminder_service.send_due_reminders(session, previous_monday) == 1
    assert reminder_service.send_due_reminders(session, datetime(2026, 3, 30, 8, tzinfo=UTC)) == 1


def test_next_run_before_monday_morning():
    assert reminder_service.next_run(datetime(2026, 10, 5, 7, 59, tzinfo=UTC)) == datetime(
        2026, 10, 5, 8, tzinfo=UTC
    )


def test_next_run_after_monday_morning():
    assert reminder_service.next_run(datetime(2026, 10, 5, 8, tzinfo=UTC)) == datetime(
        2026, 10, 12, 8, tzinfo=UTC
    )


def test_next_run_changes_utc_hour_after_daylight_saving():
    assert reminder_service.next_run(datetime(2026, 3, 23, 9, tzinfo=UTC)) == datetime(
        2026, 3, 30, 8, tzinfo=UTC
    )
    assert reminder_service.next_run(datetime(2026, 10, 19, 8, tzinfo=UTC)) == datetime(
        2026, 10, 26, 9, tzinfo=UTC
    )


def test_invitation_requires_session(client):
    assert client.post("/api/auth/reminders/invitation").status_code == 401


def test_invitation_keeps_monthly_limit(session, create_user):
    from itertools import combinations

    now = datetime.now(UTC)
    user = create_user("jmas@softcatala.org")
    interval = timedelta(days=30)
    seed_vote(session, user, now)
    prompt = session.query(Prompt).first()
    session.add_all(
        [Response(prompt_id=prompt.id, model=str(i), text="Resposta") for i in range(3, 9)]
    )
    session.commit()
    responses = session.query(Response).order_by(Response.id).all()
    existing = (responses[0].id, responses[1].id)
    pairs = [(a.id, b.id) for a, b in combinations(responses, 2) if (a.id, b.id) != existing]

    def add_votes(count, when):
        for _ in range(count):
            a, b = pairs.pop()
            session.add(
                Vote(
                    user_id=user.id,
                    prompt_id=prompt.id,
                    response_a_id=a,
                    response_b_id=b,
                    winner=Winner.a,
                    created_at=when,
                )
            )
        session.commit()

    assert not reminder_service.claim_invitation(session, user, now)
    add_votes(9, now)
    assert reminder_service.claim_invitation(session, user, now)
    assert not reminder_service.claim_invitation(session, user, now)
    assert not reminder_service.claim_invitation(session, user, now + interval + timedelta(hours=1))
    add_votes(10, now + interval / 6)
    assert not reminder_service.claim_invitation(session, user, now + interval / 6)
    assert reminder_service.claim_invitation(session, user, now + interval)
    reminder_service.set_preferences(session, user, True, now + interval)
    add_votes(10, now + interval * 2 + timedelta(hours=1))
    assert not reminder_service.claim_invitation(
        session, user, now + interval * 2 + timedelta(hours=1)
    )


def test_only_voted_comparison_does_not_send_or_consume_reminder(session, create_user, monkeypatch):
    now = datetime.now(UTC)
    user = create_user("no-active-comparisons@example.cat")
    reminder_service.set_preferences(session, user, True, now - timedelta(days=9))
    seed_vote(session, user, now)
    session.query(Response).filter(Response.model == "2").delete()
    session.commit()
    messages = []
    monkeypatch.setattr(
        reminder_service.email_service, "send_email", lambda m: messages.append(m) or True
    )
    assert reminder_service.send_due_reminders(session, now) == 0
    assert messages == []
    assert user.reminder_sent_at is None
    assert user.reminder_count == 0
    assert session.query(EmailDelivery).filter_by(kind="reminder").count() == 0


@pytest.mark.parametrize("result", [True, False, OSError("SMTP unavailable")])
def test_reminder_logs_recipient_and_result(session, create_user, monkeypatch, caplog, result):
    now = datetime.now(UTC)
    user = create_user("logging@example.cat")
    reminder_service.set_preferences(session, user, True, now - timedelta(days=9))
    seed_vote(session, user, now)

    def send(message):
        if isinstance(result, OSError):
            raise result
        return result

    monkeypatch.setattr(reminder_service.email_service, "send_email", send)
    with caplog.at_level("INFO", logger=reminder_service.__name__):
        reminder_service.send_due_reminders(session, now)
    status = "acceptat" if result is True else "fallit"
    assert f"Recordatori a logging@example.cat: {status}" in caplog.messages
