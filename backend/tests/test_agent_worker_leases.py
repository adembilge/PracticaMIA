"""Synthetic queue recovery and worker fencing."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import sessionmaker

from app.agent.checkpoints import (
    CheckpointConflict, CheckpointState, load_checkpoint, submit_clarification_reply,
)
from app.agent.contract import AnswerResult, ClarificationReply, ClarifyingQuestion
from app.agent.run_events import AgentRunEvent, InvalidClarificationReply, read_run_events, read_run_snapshot
from app.agent.run_requests import AgentRunRequest
from app.agent.worker import RequestClarification, run_next_worker_step, run_worker_step
from app.agent.worker_leases import WorkerLeaseConflict, claim_next_run
from app.auth.tokens import Principal
from test_agent_run_events import queued_run  # noqa: F401 - shared run fixture


LEASE_FOR = timedelta(minutes=1)
ANSWER = AnswerResult(explanation="Synthetic answer", verification_status="insufficient_evidence")


def _expire(db, run_id):
    db.get(AgentRunRequest, str(run_id)).lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)


def test_scheduler_reclaims_an_interrupted_run_at_its_checkpoint(queued_run):
    factory, context, _, _ = queued_run
    options = {"lease_for": LEASE_FOR, "key": context["key"]}
    called = []

    def advance(_, state):
        called.append(state.next_node)
        return CheckpointState(next_node="identify_intent")

    assert run_next_worker_step(factory, **options, execute=advance).last_event_seq == 2

    def crash(_, state):
        called.append(state.next_node)
        raise RuntimeError("synthetic worker halted")

    with pytest.raises(RuntimeError, match="worker halted"):
        run_next_worker_step(factory, **options, execute=crash)
    assert run_next_worker_step(factory, **options, execute=lambda *_: pytest.fail("lease held")) is None

    with factory.begin() as db:
        _expire(db, context["run_id"])

    def finish(_, state):
        called.append(state.next_node)
        return ANSWER

    completed = run_next_worker_step(factory, **options, execute=finish)
    assert completed.status == "completed"
    assert completed.last_event_seq == 3
    assert called == ["load_context", "identify_intent", "identify_intent"]
    assert run_next_worker_step(factory, **options, execute=lambda *_: pytest.fail("no work")) is None


def test_lost_lease_is_fenced_at_commit(queued_run):
    factory, context, _, _ = queued_run
    with factory.begin() as db:
        first = claim_next_run(db, lease_for=LEASE_FOR)
        assert claim_next_run(db, lease_for=LEASE_FOR) is None

    with pytest.raises(WorkerLeaseConflict, match="requires"):
        run_worker_step(factory, **context, execute=lambda *_: pytest.fail("lease required"))

    def expire_before_commit(*_):
        with factory.begin() as db:
            _expire(db, first.run_id)
        return ANSWER

    with pytest.raises(WorkerLeaseConflict, match="no longer current"):
        run_worker_step(factory, **context, lease=first, execute=expire_before_commit)

    with factory.begin() as db:
        second = claim_next_run(db, lease_for=LEASE_FOR)
        assert second.run_id == first.run_id
        assert second.token != first.token
    with pytest.raises(WorkerLeaseConflict, match="no longer current"):
        run_worker_step(factory, **context, lease=first, execute=lambda *_: pytest.fail("stale lease"))

    assert run_worker_step(factory, **context, lease=second, execute=lambda *_: ANSWER).status == "completed"
    with factory.begin() as db:
        assert [item.type for item in read_run_events(db, **context, after_seq=0).events] == [
            "run.started", "answer.completed",
        ]


def test_worker_persists_a_pending_question_and_reconnect_replays_it(queued_run):
    factory, context, _, _ = queued_run
    options = {"lease_for": LEASE_FOR, "key": context["key"]}
    assert run_next_worker_step(factory, **options, execute=lambda *_: CheckpointState(
        next_node="choose_next_step",
    )).last_event_seq == 2
    question = ClarifyingQuestion(
        question_id=uuid4(), text="Qual è il comune di provenienza?",
        answer_shape="free_text", missing_fields=["origin_municipality"],
    )
    snapshot = run_next_worker_step(factory, **options, execute=lambda *_: RequestClarification(
        question, CheckpointState(next_node="find_evidence", missing_fields=question.missing_fields),
    ))
    assert (snapshot.status, snapshot.last_event_seq) == ("waiting_for_information", 3)

    replacement = sessionmaker(bind=factory.kw["bind"])
    assert run_next_worker_step(replacement, **options, execute=lambda *_: pytest.fail("waiting for input")) is None
    with replacement.begin() as db:
        run = db.get(AgentRunRequest, str(context["run_id"]))
        assert run.lease_token is None and run.lease_expires_at is None
        assert read_run_snapshot(db, **context) == snapshot
        page = read_run_events(db, **context, after_seq=2)
        assert [event.type for event in page.events] == ["question.requested"]
        assert page.events[0].question == question
        assert question.text.encode() not in db.get(AgentRunEvent, (run.id, 3)).ciphertext
        checkpoint = load_checkpoint(db, **context)
        assert checkpoint.event_seq == page.last_event_seq
        assert checkpoint.state.next_node == "find_evidence"
        assert checkpoint.state.pending_question_id == question.question_id


def test_invalid_question_rolls_back_the_pause_and_worker_can_retry(queued_run):
    factory, context, _, _ = queued_run
    options = {"lease_for": LEASE_FOR, "key": context["key"]}
    question = ClarifyingQuestion(
        question_id=uuid4(), text="Which city?", answer_shape="free_text", missing_fields=["jurisdiction"],
    )
    resume_state = CheckpointState(next_node="find_evidence")
    malformed = question.model_copy(update={"missing_fields": []})
    with pytest.raises(ValidationError, match="missing_fields"):
        run_next_worker_step(factory, **options, execute=lambda *_: RequestClarification(malformed, resume_state))

    with factory.begin() as db:
        assert read_run_snapshot(db, **context).status == "running"
        assert read_run_events(db, **context, after_seq=1).events == []
        checkpoint = load_checkpoint(db, **context)
        assert checkpoint.event_seq == 1 and checkpoint.state.pending_question_id is None
        _expire(db, context["run_id"])

    paused = run_next_worker_step(factory, **options, execute=lambda *_: RequestClarification(question, resume_state))
    assert (paused.status, paused.last_event_seq) == ("waiting_for_information", 2)


def test_accepted_reply_resumes_the_same_run_and_survives_a_worker_restart(queued_run):
    factory, context, _, _ = queued_run
    options = {"lease_for": LEASE_FOR, "key": context["key"]}
    question = ClarifyingQuestion(
        question_id=uuid4(), text="Which city?", answer_shape="free_text", missing_fields=["jurisdiction"],
    )
    paused = run_next_worker_step(factory, **options, execute=lambda *_: RequestClarification(
        question, CheckpointState(next_node="find_evidence"),
    ))
    reply = ClarificationReply(
        client_reply_id=uuid4(), expected_run_revision=paused.run_revision, text="Comune sintetico",
    )

    with factory.begin() as db:
        accepted = submit_clarification_reply(db, **context, question_id=question.question_id, reply=reply)
        checkpoint = load_checkpoint(db, **context)
        assert checkpoint.state.pending_question_id is None
        assert checkpoint.event_seq == accepted.event_seq
        assert read_run_snapshot(db, **context).status == "running"
        row = db.get(AgentRunEvent, (str(context["run_id"]), accepted.event_seq))
        assert reply.text.encode() not in row.ciphertext

    def resume(message, state):
        assert message.text == "Fixture domanda sulla residenza"
        assert message.clarification_reply == accepted
        assert state.next_node == "find_evidence"

    def crash(message, state):
        resume(message, state)
        raise RuntimeError("synthetic interruption after reading the reply")

    with pytest.raises(RuntimeError, match="synthetic interruption"):
        run_next_worker_step(factory, **options, execute=crash)

    with factory.begin() as db:
        _expire(db, context["run_id"])

    def finish(message, state):
        resume(message, state)
        return ANSWER

    replacement = sessionmaker(bind=factory.kw["bind"])
    completed = run_next_worker_step(replacement, **options, execute=finish)
    assert completed.run_id == paused.run_id
    assert completed.status == "completed"
    with replacement.begin() as db:
        assert submit_clarification_reply(db, **context, question_id=question.question_id, reply=reply) == accepted
        events = read_run_events(db, **context, after_seq=paused.last_event_seq).events
        assert [event.type for event in events] == ["question.answered", "answer.completed"]
        assert events[0] == accepted


def test_only_the_owner_can_answer_the_current_question_with_a_valid_choice(queued_run):
    factory, context, _, _ = queued_run
    question = ClarifyingQuestion(
        question_id=uuid4(), text="Which option?", answer_shape="single_choice",
        options=["First", "Second"], missing_fields=["jurisdiction"],
    )
    paused = run_worker_step(factory, **context, execute=lambda *_: RequestClarification(
        question, CheckpointState(next_node="find_evidence"),
    ))
    reply = ClarificationReply(
        client_reply_id=uuid4(), expected_run_revision=paused.run_revision, text="Second",
    )

    with factory.begin() as db:
        assert submit_clarification_reply(
            db, **{**context, "principal": Principal("different-owner")},
            question_id=question.question_id, reply=reply,
        ) is None
        with pytest.raises(CheckpointConflict, match="no longer pending"):
            submit_clarification_reply(db, **context, question_id=uuid4(), reply=reply)
        with pytest.raises(CheckpointConflict, match="no longer pending"):
            submit_clarification_reply(db, **context, question_id=question.question_id, reply=reply.model_copy(
                update={"expected_run_revision": paused.run_revision - 1},
            ))
        with pytest.raises(InvalidClarificationReply, match="offered choices"):
            submit_clarification_reply(db, **context, question_id=question.question_id, reply=reply.model_copy(
                update={"text": "Third"},
            ))
        assert read_run_snapshot(db, **context) == paused
        accepted = submit_clarification_reply(db, **context, question_id=question.question_id, reply=reply)

    next_question = question.model_copy(update={"question_id": uuid4()})
    next_pause = run_worker_step(factory, **context, execute=lambda *_: RequestClarification(
        next_question, CheckpointState(next_node="find_evidence"),
    ))
    with factory.begin() as db:
        assert submit_clarification_reply(db, **context, question_id=question.question_id, reply=reply) == accepted
        with pytest.raises(CheckpointConflict, match="no longer pending"):
            submit_clarification_reply(db, **context, question_id=question.question_id, reply=reply.model_copy(
                update={"text": "First"},
            ))
        assert read_run_snapshot(db, **context) == next_pause
        with pytest.raises(CheckpointConflict, match="no longer pending"):
            submit_clarification_reply(db, **context, question_id=question.question_id, reply=reply.model_copy(
                update={"expected_run_revision": next_pause.run_revision},
            ))
