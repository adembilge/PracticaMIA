"""Synthetic coverage for the encrypted run journal and reconnect cursor."""

from datetime import datetime, timezone
from os import urandom
from uuid import uuid4

import pytest
from cryptography.exceptions import InvalidTag

from app.agent.contract import agent_event_adapter
from app.agent.run_events import (
    AgentRunEvent, EventConflict, _event_aad, append_run_event, read_run_events, read_run_snapshot,
)
from app.agent.run_requests import AgentRunRequest, _payload_cipher, accept_message
from app.agent.threads import create_thread
from app.auth.tokens import Principal
from test_agent_contract import ANSWER, PASSAGE
from test_agent_run_requests import ALICE, KEY, request


@pytest.fixture
def queued_run(client):
    factory = client.app.state.session_factory
    message = request()
    with factory.begin() as db:
        thread_id = create_thread(db, principal=ALICE)
        run = accept_message(db, thread_id=thread_id, principal=ALICE, message=message, key=KEY)
    context = {"thread_id": thread_id, "run_id": run.run_id, "principal": ALICE, "key": KEY}

    def event(event_type, seq, **payload):
        return agent_event_adapter.validate_python({
            "schema_version": 1, "thread_id": thread_id, "run_id": run.run_id,
            "event_seq": seq, "type": event_type, "occurred_at": datetime.now(timezone.utc),
            **payload,
        })

    started = event("run.started", 1, client_message_id=message.client_message_id)
    return factory, context, started, event


def _append(db, context, event):
    return append_run_event(db, principal=context["principal"], key=context["key"], event=event)


def test_reconnect_reads_the_missing_pages_and_terminal_result(queued_run):
    factory, context, started, event = queued_run
    progress = event("progress.updated", 2, stage="test", text="Synthetic private status")
    terminal = event("answer.completed", 3, result={
        "explanation": "No official evidence was found.",
        "verification_status": "insufficient_evidence",
    })

    with factory.begin() as db:
        assert read_run_snapshot(db, **context).status == "queued"
        assert read_run_events(db, **context, after_seq=0).events == []
        for item in (started, progress, terminal):
            assert _append(db, context, item) == item

    with factory.begin() as db:  # Reopen the session to simulate a reconnect.
        first = read_run_events(db, **context, after_seq=0, limit=2)
        assert first.events == [started, progress]
        assert first.has_more and first.last_event_seq == 2

        second = read_run_events(db, **context, after_seq=first.last_event_seq, limit=2)
        assert second.events == [terminal]
        assert not second.has_more and second.last_event_seq == 3

        finished = read_run_snapshot(db, **context)
        assert finished.status == "completed"
        assert finished.result == terminal.result
        assert (finished.last_event_seq, finished.run_revision) == (3, 4)
        assert read_run_events(db, **context, after_seq=3).last_event_seq == 3
        assert b"Synthetic private status" not in db.get(
            AgentRunEvent, (str(context["run_id"]), 2),
        ).ciphertext
        with pytest.raises(ValueError, match="cursor"):
            read_run_events(db, **context, after_seq=4)
        with pytest.raises(ValueError, match="page size"):
            read_run_events(db, **context, after_seq=0, limit=101)


def test_retries_are_stable_and_state_rejects_invalid_events(queued_run):
    factory, context, started, event = queued_run
    with factory.begin() as db:
        with pytest.raises(EventConflict, match="sequence"):
            _append(db, context, event("progress.updated", 2, stage="test", text="gap"))
        with pytest.raises(EventConflict, match="accepted message"):
            _append(db, context, event("run.started", 1, client_message_id=uuid4()))
        _append(db, context, started)
        assert _append(db, context, started) == started
        with pytest.raises(EventConflict, match="occupied"):
            _append(db, context, started.model_copy(update={"client_message_id": uuid4()}))
        with pytest.raises(EventConflict, match="run's case"):
            _append(db, context, event("approval.requested", 2, proposal={
                "proposal_id": uuid4(), "case_id": uuid4(), "field_id": "destination_municipality",
                "previous_value": None, "proposed_value": "example", "rationale": "Fixture",
                "expected_case_revision": 1, "expires_at": datetime.now(timezone.utc),
            }))

        question = event("question.requested", 2, question={
            "question_id": uuid4(), "text": "Which city?", "answer_shape": "free_text",
            "missing_fields": ["jurisdiction"],
        })
        _append(db, context, question)
        _append(db, context, event("progress.updated", 3, stage="waiting", text="Waiting for answer"))
        assert read_run_snapshot(db, **context).status == "waiting_for_information"
        stopped = event("run.stopped", 4, committed_operation_ids=[])
        _append(db, context, stopped)
        assert _append(db, context, stopped) == stopped
        assert read_run_snapshot(db, **context).status == "stopped"
        with pytest.raises(EventConflict, match="run state"):
            _append(db, context, event("progress.updated", 5, stage="test", text="late"))


def test_journal_requires_claim_links_for_new_verified_answers_and_official_channels(queued_run):
    factory, context, started, event = queued_run
    claim = {"kind": "channel", "statement": "The synthetic source identifies a contact.", "evidence_ids": [PASSAGE]}
    with factory.begin() as db:
        _append(db, context, started)
        with pytest.raises(EventConflict, match="verified answer requires evidence-linked claims"):
            _append(db, context, event("answer.completed", 2, result=ANSWER))
        with pytest.raises(EventConflict, match="official channel requires an evidence-linked channel claim"):
            _append(db, context, event("answer.completed", 2, result={
                **ANSWER, "verification_status": "insufficient_evidence", "claims": [{**claim, "kind": "authority"}],
            }))
        assert read_run_snapshot(db, **context).status == "running"
        linked = event("answer.completed", 2, result={**ANSWER, "claims": [claim]})
        assert _append(db, context, linked) == linked
    with factory() as db:
        assert read_run_snapshot(db, **context).result.claims == linked.result.claims
        assert read_run_events(db, **context, after_seq=1).events == [linked]


def test_legacy_encrypted_verified_answer_without_claims_remains_readable(queued_run):
    factory, context, started, event = queued_run
    legacy = event("answer.completed", 2, result=ANSWER)
    with factory.begin() as db:
        _append(db, context, started)
        row = db.get(AgentRunRequest, str(context["run_id"]))
        payload = legacy.model_dump_json(exclude_unset=True).encode()
        assert b'"claims"' not in payload
        nonce = urandom(12)
        ciphertext = _payload_cipher(KEY).encrypt(nonce, payload, _event_aad(row, 2, ALICE))
        db.add(AgentRunEvent(run_id=row.id, event_seq=2, ciphertext=nonce + ciphertext))
        row.status = "completed"
    with factory.begin() as db:
        assert read_run_snapshot(db, **context).result == legacy.result
        assert read_run_events(db, **context, after_seq=1).events == [legacy]
        assert _append(db, context, legacy) == legacy


def test_wrong_owner_cannot_replay_or_append_and_rolled_back_events_are_absent(queued_run):
    factory, context, started, _ = queued_run
    with factory() as db:
        other = {**context, "principal": Principal("other-owner")}
        assert read_run_snapshot(db, **other) is None
        assert read_run_events(db, **other, after_seq=0) is None
        assert _append(db, other, started) is None
        _append(db, context, started)
        assert read_run_snapshot(db, **context).status == "running"
        db.rollback()

    with factory.begin() as db:
        assert read_run_snapshot(db, **context).status == "queued"
        assert read_run_events(db, **context, after_seq=0).events == []
        _append(db, context, started)


def test_corrupted_event_payload_fails_authentication(queued_run):
    factory, context, started, event = queued_run
    with factory.begin() as db:
        _append(db, context, started)
        _append(db, context, event("progress.updated", 2, stage="test", text="private"))
        row = db.get(AgentRunEvent, (str(context["run_id"]), 1))
        other = db.get(AgentRunEvent, (str(context["run_id"]), 2))
        row.ciphertext = other.ciphertext
        with pytest.raises(InvalidTag):
            read_run_events(db, **context, after_seq=0)
