"""Synthetic worker recovery and transaction tests."""

from uuid import uuid4

import pytest
from cryptography.exceptions import InvalidTag
from pydantic import ValidationError

from app.agent.checkpoints import (
    AgentRunCheckpoint, CheckpointConflict, CheckpointState, load_checkpoint, save_checkpoint,
)
from app.agent.run_events import append_run_event, read_run_events, read_run_snapshot
from app.auth.tokens import Principal
from test_agent_run_events import queued_run  # noqa: F401 - shared synthetic run fixture


def test_new_worker_recovers_next_node_and_stale_worker_cannot_replace_it(queued_run):
    factory, context, started, event = queued_run
    with factory.begin() as db:
        assert load_checkpoint(db, **context) is None
        first = save_checkpoint(
            db, **context, expected_revision=0, expected_event_seq=0,
            state=CheckpointState(next_node="identify_intent"), event=started,
        )
        assert (first.revision, first.event_seq) == (1, 1)

    with factory.begin() as db:
        assert load_checkpoint(db, **context) == first
        state = CheckpointState(
            next_node="find_evidence", intent="find_procedure",
            procedure_candidates=["example_procedure"],
        )
        second = save_checkpoint(
            db, **context, expected_revision=first.revision, expected_event_seq=first.event_seq,
            state=state,
        )
        assert (second.revision, second.event_seq) == (2, 1)
        with pytest.raises(CheckpointConflict, match="changed"):
            save_checkpoint(
                db, **context, expected_revision=first.revision, expected_event_seq=first.event_seq,
                state=first.state,
            )
        assert load_checkpoint(db, **context) == second
        ciphertext = db.get(
            AgentRunCheckpoint, str(context["run_id"]),
        ).ciphertext
        assert b"example_procedure" not in ciphertext
        assert b"find_procedure" not in ciphertext

        progress = event("progress.updated", 2, stage="search", text="Searching")
        append_run_event(db, principal=context["principal"], key=context["key"], event=progress)
        with pytest.raises(CheckpointConflict, match="reconciliation"):
            load_checkpoint(db, **context)
        with pytest.raises(CheckpointConflict, match="watermark"):
            save_checkpoint(
                db, **context, expected_revision=second.revision, expected_event_seq=second.event_seq,
                state=state,
            )


def test_waiting_state_and_event_are_committed_or_rolled_back_together(queued_run):
    factory, context, started, event = queued_run
    with factory.begin() as db:
        save_checkpoint(
            db, **context, expected_revision=0, expected_event_seq=0,
            state=CheckpointState(next_node="identify_intent"), event=started,
        )

    question_id = uuid4()
    question = event("question.requested", 2, question={
        "question_id": question_id, "text": "Which city?", "answer_shape": "free_text",
        "missing_fields": ["jurisdiction"],
    })
    pending = CheckpointState(next_node="load_context", pending_question_id=question_id)
    with factory() as db:
        with pytest.raises(CheckpointConflict, match="pending question"):
            save_checkpoint(
                db, **context, expected_revision=1, expected_event_seq=1,
                state=CheckpointState(next_node="load_context"), event=question,
            )
        assert read_run_events(db, **context, after_seq=1).events == []
        save_checkpoint(
            db, **context, expected_revision=1, expected_event_seq=1, state=pending, event=question,
        )
        assert read_run_snapshot(db, **context).status == "waiting_for_information"
        db.rollback()

    with factory.begin() as db:
        assert read_run_snapshot(db, **context).status == "running"
        assert read_run_events(db, **context, after_seq=1).events == []
        assert load_checkpoint(db, **context).revision == 1
        saved = save_checkpoint(
            db, **context, expected_revision=1, expected_event_seq=1, state=pending, event=question,
        )
        assert load_checkpoint(db, **context) == saved
        assert read_run_events(db, **context, after_seq=1).events == [question]


def test_checkpoint_scope_and_terminal_run_cannot_resume(queued_run):
    factory, context, started, event = queued_run
    state = CheckpointState(next_node="verify_and_respond")
    with factory.begin() as db:
        save_checkpoint(
            db, **context, expected_revision=0, expected_event_seq=0,
            state=state, event=started,
        )
        foreign = {**context, "principal": Principal("other-owner")}
        assert load_checkpoint(db, **foreign) is None
        assert save_checkpoint(
            db, **foreign, expected_revision=1, expected_event_seq=1, state=state,
        ) is None
        stopped = event("run.stopped", 2, committed_operation_ids=[])
        append_run_event(db, principal=context["principal"], key=context["key"], event=stopped)
        assert load_checkpoint(db, **context) is None
        with pytest.raises(CheckpointConflict, match="terminal"):
            save_checkpoint(db, **context, expected_revision=1, expected_event_seq=2, state=state)


@pytest.mark.parametrize("intent", [
    "request_information", "find_procedure", "explain_notice", "explain_form_field",
    "resume_case", "plan_multiple_tasks",
])
def test_checkpoint_accepts_defined_intent_labels(intent):
    state = CheckpointState.model_validate({"next_node": "find_evidence", "intent": intent})
    assert CheckpointState.model_validate_json(state.model_dump_json()).intent == intent


def test_old_checkpoint_can_resume_without_intent():
    state = CheckpointState.model_validate_json(
        '{"schema_version":1,"next_node":"find_evidence","procedure_candidates":["example_procedure"]}',
    )
    assert state.intent is None
    assert state.procedure_candidates == ["example_procedure"]


@pytest.mark.parametrize("intent", ["submit_application", "Find procedure", {"kind": "resume_case"}])
def test_checkpoint_rejects_undefined_intents(intent):
    with pytest.raises(ValidationError, match="intent"):
        CheckpointState.model_validate({"next_node": "find_evidence", "intent": intent})


def test_checkpoint_rejects_raw_state_and_detects_metadata_tampering(queued_run):
    factory, context, started, _ = queued_run
    with pytest.raises(ValidationError):
        CheckpointState.model_validate({"next_node": "load_context", "raw_message": "private"})
    with factory.begin() as db:
        save_checkpoint(
            db, **context, expected_revision=0, expected_event_seq=0,
            state=CheckpointState(next_node="identify_intent"), event=started,
        )
        row = db.get(AgentRunCheckpoint, str(context["run_id"]))
        row.revision += 1
        with pytest.raises(InvalidTag):
            load_checkpoint(db, **context)
