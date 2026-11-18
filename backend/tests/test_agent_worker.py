"""Exercise durable worker recovery using synthetic, read-only steps."""

from uuid import uuid4

import pytest
from sqlalchemy.orm import sessionmaker

from app.agent.checkpoints import AgentRunCheckpoint, CheckpointConflict, CheckpointState, load_checkpoint
from app.agent.contract import AnswerResult
from app.agent.run_events import append_run_event, read_run_events, read_run_snapshot
from app.agent.worker import run_worker_step
from app.auth.tokens import Principal
from test_agent_run_events import queued_run  # noqa: F401 - shared synthetic run fixture


def test_replacement_worker_skips_completed_node_after_interruption(queued_run):
    factory, context, _, _ = queued_run
    calls = []

    def first(message, state):
        assert message.text
        calls.append(state.next_node)
        return CheckpointState(next_node="identify_intent")

    assert run_worker_step(factory, **context, execute=first).last_event_seq == 2

    def interrupted(_message, state):
        calls.append(state.next_node)
        raise RuntimeError("synthetic interruption before checkpoint commit")

    with pytest.raises(RuntimeError, match="synthetic interruption"):
        run_worker_step(factory, **context, execute=interrupted)

    replacement = sessionmaker(bind=factory.kw["bind"])

    def resumed(_message, state):
        calls.append(state.next_node)
        return CheckpointState(next_node="verify_and_respond")

    assert run_worker_step(replacement, **context, execute=resumed).last_event_seq == 3

    def finish(_message, state):
        calls.append(state.next_node)
        return AnswerResult(
            explanation="There is no applicable evidence in this fixture.",
            verification_status="insufficient_evidence",
        )

    snapshot = run_worker_step(replacement, **context, execute=finish)
    assert snapshot.status == "completed"
    assert snapshot.result.verification_status == "insufficient_evidence"
    assert calls == ["load_context", "identify_intent", "identify_intent", "verify_and_respond"]
    assert run_worker_step(replacement, **context, execute=lambda *_: pytest.fail("already done")) == snapshot
    with replacement.begin() as db:
        assert read_run_events(db, **context, after_seq=2).events[-1].type == "answer.completed"
        assert db.get(AgentRunCheckpoint, str(context["run_id"])) is None


def test_stale_worker_cannot_commit_its_terminal_answer(queued_run):
    factory, context, _, _ = queued_run

    def stale(_message, _state):
        result = run_worker_step(factory, **context, execute=lambda *_: CheckpointState(
            next_node="find_evidence",
        ))
        assert result.last_event_seq == 2
        return AnswerResult(explanation="Stale result", verification_status="unsupported")

    with pytest.raises(CheckpointConflict, match="watermark"):
        run_worker_step(factory, **context, execute=stale)
    with factory.begin() as db:
        saved = load_checkpoint(db, **context)
        assert saved.state.next_node == "find_evidence"
        assert read_run_snapshot(db, **context).status == "running"
        assert all(item.type != "answer.completed" for item in read_run_events(db, **context, after_seq=0).events)


def test_worker_does_not_execute_foreign_or_waiting_run(queued_run):
    factory, context, _, event = queued_run

    def must_not_execute(*_):
        pytest.fail("the callback should not be called")

    assert run_worker_step(
        factory, **{**context, "principal": Principal("other-owner")}, execute=must_not_execute,
    ) is None

    run_worker_step(factory, **context, execute=lambda *_: CheckpointState(next_node="identify_intent"))
    question = event("question.requested", 3, question={
        "question_id": uuid4(), "text": "Which city?", "answer_shape": "free_text",
        "missing_fields": ["jurisdiction"],
    })
    with factory.begin() as db:
        append_run_event(db, principal=context["principal"], key=context["key"], event=question)
    assert run_worker_step(factory, **context, execute=must_not_execute).status == "waiting_for_information"
