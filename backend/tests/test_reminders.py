"""Proves dels recordatoris voluntaris i dels límits d'enviament."""

from datetime import UTC, datetime, timedelta

from app.models import Category, Prompt, Response, Vote, Winner
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
