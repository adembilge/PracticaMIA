"""Advance one durable step of an owned run in the internal agent service."""

from collections.abc import Callable
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from app.agent.checkpoints import (
    CheckpointConflict, CheckpointState, finish_checkpoint, load_checkpoint, save_checkpoint,
)
from app.agent.contract import AnswerCompleted, AnswerResult, ProgressUpdated, RunSnapshot, RunStarted
from app.agent.run_events import read_run_snapshot
from app.agent.run_requests import AgentRunRequest, StoredMessage, _owned_run, read_run_message
from app.auth.tokens import Principal


def run_worker_step(
    sessions: sessionmaker[Session], *, thread_id: UUID, run_id: UUID,
    principal: Principal, key: bytes,
    execute: Callable[[StoredMessage, CheckpointState], CheckpointState | AnswerResult],
) -> RunSnapshot | None:
    """Run a side-effect-free step between short database transactions."""
    context = {"thread_id": thread_id, "run_id": run_id, "principal": principal, "key": key}
    with sessions.begin() as db:
        # Use an exclusive lock before initializing so two workers never need
        # to upgrade a shared lock on the same queued run.
        run = db.scalar(_owned_run(thread_id, run_id, principal).with_for_update(
            of=AgentRunRequest,
        ))
        if run is None:
            return None
        if run.status not in ("queued", "running"):
            return read_run_snapshot(db, **context)
        checkpoint = load_checkpoint(db, **context)
        if run.status == "queued":
            if checkpoint is not None:
                raise CheckpointConflict("Queued run already has a checkpoint")
            started = RunStarted(
                schema_version=1, thread_id=thread_id, run_id=run_id, event_seq=1,
                occurred_at=datetime.now(timezone.utc), type="run.started",
                client_message_id=UUID(run.client_message_id),
            )
            checkpoint = save_checkpoint(
                db, **context, expected_revision=0, expected_event_seq=0,
                state=CheckpointState(next_node="load_context"), event=started,
            )
        if checkpoint is None:
            raise CheckpointConflict("Running worker has no checkpoint")
        message = read_run_message(db, **context)
        if message is None:
            return None

    # Only completed boundaries survive a crash. Uncommitted computation can
    # run again, so this callback must not perform external writes.
    result = execute(message, checkpoint.state.model_copy(deep=True))
    with sessions.begin() as db:
        boundary = {
            "expected_revision": checkpoint.revision,
            "expected_event_seq": checkpoint.event_seq,
        }
        envelope = {
            "schema_version": 1, "thread_id": thread_id, "run_id": run_id,
            "event_seq": checkpoint.event_seq + 1, "occurred_at": datetime.now(timezone.utc),
        }
        if isinstance(result, AnswerResult):
            finish_checkpoint(
                db, principal=principal, key=key, **boundary,
                event=AnswerCompleted(**envelope, type="answer.completed", result=result),
            )
        else:
            save_checkpoint(
                db, **context, **boundary, state=result,
                event=ProgressUpdated(
                    **envelope, type="progress.updated", stage=checkpoint.state.next_node,
                    text="Worker step recorded.",
                ),
            )
        return read_run_snapshot(db, **context)
