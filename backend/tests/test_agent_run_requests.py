"""Synthetic coverage for encrypted, owner-scoped message acceptance."""

from uuid import UUID, uuid4

import pytest
from cryptography.exceptions import InvalidTag
from sqlalchemy import select

from app.agent.contract import SendMessage
from app.agent.run_requests import AgentRunRequest, accept_message, read_run_message
from app.agent.threads import AgentThread, create_thread, link_case_to_thread
from app.auth.tokens import Principal


KEY = bytes(range(32))
ALICE = Principal("alice")
BOB = Principal("bob")


def request(**overrides):
    return SendMessage(
        **{"client_message_id": uuid4(), "text": "Fixture domanda sulla residenza", "language": "it", **overrides}
    )


def test_accepted_message_resumes_after_session_restart_and_replays_exactly(client):
    factory = client.app.state.session_factory
    message = request(expected_thread_revision=1)
    with factory.begin() as db:
        thread_id = create_thread(db, principal=ALICE)
        accepted = accept_message(db, thread_id=thread_id, principal=ALICE, message=message, key=KEY)
        assert accepted.outcome == "accepted"
        assert accepted.accepted_revision == 2

    with factory.begin() as db:
        context = {"thread_id": thread_id, "principal": ALICE, "key": KEY}
        row = db.get(AgentRunRequest, str(accepted.run_id))
        assert message.text.encode() not in row.message_ciphertext
        assert row.status == "queued"
        assert accept_message(db, **context, message=message) == accepted
        assert accept_message(db, **context, message=message.model_copy(
            update={"expected_thread_revision": 2},
        )) == accepted
        for change in ({"text": "Different text"}, {"language": "en"}):
            altered = message.model_copy(update=change)
            assert accept_message(db, **context, message=altered).outcome == "message_conflict"
        assert accept_message(db, **context, message=request(
            expected_thread_revision=1,
        )).outcome == "stale_thread"
        assert accept_message(db, **context, message=request(
            expected_thread_revision=2,
        )).outcome == "active_run"
        assert db.get(AgentThread, str(thread_id)).revision == 2
        found = read_run_message(db, **context, run_id=accepted.run_id)
        assert found.text == message.text
        assert found.language == "it"
        assert found.case_id is None
        assert read_run_message(
            db, thread_id=thread_id, run_id=accepted.run_id, principal=BOB, key=KEY,
        ) is None

        row.status = "failed"  # The next execution slice owns terminal transitions.
        new = accept_message(db, **context, message=request(expected_thread_revision=2))
        assert new.outcome == "accepted"
        assert new.accepted_revision == 3
        assert new.run_id != accepted.run_id
        assert accept_message(db, **context, message=message) == accepted


def test_case_ownership_link_and_thread_are_required_on_writer_and_reader(client, auth_headers):
    first_case = UUID(client.post("/api/v1/cases", headers=auth_headers("alice"), json={}).json()["id"])
    second_case = UUID(client.post("/api/v1/cases", headers=auth_headers("alice"), json={}).json()["id"])
    factory = client.app.state.session_factory
    with factory.begin() as db:
        thread_id = create_thread(db, principal=ALICE)
        unlinked_thread = create_thread(db, principal=ALICE)
        context = {"thread_id": thread_id, "principal": ALICE, "key": KEY}
        message = request(case_id=first_case)
        assert accept_message(db, **context, message=message).outcome == "unavailable"
        assert link_case_to_thread(db, principal=ALICE, thread_id=thread_id, case_id=first_case)
        assert link_case_to_thread(db, principal=ALICE, thread_id=thread_id, case_id=second_case)
        accepted = accept_message(db, **context, message=message)
        assert accepted.outcome == "accepted"
        assert accept_message(db, **context, message=message.model_copy(
            update={"case_id": second_case},
        )).outcome == "message_conflict"
        assert accept_message(
            db, thread_id=thread_id, principal=BOB, message=message, key=KEY,
        ).outcome == "unavailable"
        assert read_run_message(db, **context, run_id=accepted.run_id).case_id == first_case
        assert read_run_message(
            db, thread_id=unlinked_thread, principal=ALICE, run_id=accepted.run_id, key=KEY,
        ) is None

    assert client.delete(f"/api/v1/cases/{first_case}", headers=auth_headers("alice")).status_code == 204
    with factory.begin() as db:
        assert read_run_message(db, **context, run_id=accepted.run_id) is None
        assert accept_message(db, **context, message=message).outcome == "unavailable"


def test_tampered_messages_fail_authentication_and_bad_key_does_not_advance_thread(client):
    with client.app.state.session_factory.begin() as db:
        thread_id = create_thread(db, principal=ALICE)
        with pytest.raises(ValueError, match="256-bit"):
            accept_message(db, thread_id=thread_id, principal=ALICE, message=request(), key=KEY[:16])
        assert db.get(AgentThread, str(thread_id)).revision == 1
        assert db.scalars(select(AgentRunRequest)).all() == []

        accepted = accept_message(db, thread_id=thread_id, principal=ALICE, message=request(), key=KEY)
        row = db.get(AgentRunRequest, str(accepted.run_id))
        row.message_ciphertext = row.message_ciphertext[:-1] + bytes([row.message_ciphertext[-1] ^ 1])
        with pytest.raises(InvalidTag):
            read_run_message(db, thread_id=thread_id, principal=ALICE, run_id=accepted.run_id, key=KEY)
