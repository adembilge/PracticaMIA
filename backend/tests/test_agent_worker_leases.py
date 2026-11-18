"""Synthetic queue recovery and worker fencing."""

from datetime import datetime, timedelta, timezone

import pytest

from app.agent.checkpoints import CheckpointState
from app.agent.contract import AnswerResult
from app.agent.run_events import read_run_events
from app.agent.run_requests import AgentRunRequest
from app.agent.worker import run_next_worker_step, run_worker_step
from app.agent.worker_leases import WorkerLeaseConflict, claim_next_run
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
