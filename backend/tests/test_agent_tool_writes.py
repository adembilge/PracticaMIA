"""Exercise committed retry receipts and real PostgreSQL serialization."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.agent.threads import AgentThread, create_thread, link_case_to_thread
from app.agent.tool_access import ToolAccessDenied
from app.agent.tool_writes import AgentCaseOperation, CaseOperationConflict, apply_approved_case_update
from app.cases.intake_model import CaseIntake
from app.cases.model import CaseRecord
from test_agent_run_requests import ALICE, BOB, KEY
from test_agent_tool_access import _run, tool_run  # noqa: F401 - shared owned-run fixture
from test_agent_tool_execution import _save_pending


def _pending(factory, scope, case_id):
    context = {**scope, "principal": ALICE, "key": KEY}
    _, call, approval = _save_pending(factory, context, case_id, datetime.now(timezone.utc) + timedelta(minutes=5))
    return context, call, approval


def _write_intake(db, proposal):
    db.add(CaseIntake(
        case_id=str(proposal.case_id), owner_subject=ALICE.subject,
        facts={proposal.field_id: proposal.proposed_value},
    ))
    db.flush()
    return proposal.expected_case_revision + 1


@pytest.fixture
def approved_update(client, tool_run):
    scope, _, case_id, _, _ = tool_run
    factory = client.app.state.session_factory
    context, call, approval = _pending(factory, scope, case_id)
    return factory, context, call, approval


def test_committed_receipt_replays_and_conflicts_are_denied(approved_update):
    factory, context, call, approval = approved_update
    result = apply_approved_case_update(factory, **context, call=call,
                                        read_approval=lambda *_: approval, write_case=_write_intake)

    # A new connection after a lost response must not need to inspect current approvals or rewrite a case.
    restarted = sessionmaker(bind=factory.kw["bind"])

    def unexpected(*_):
        pytest.fail("an existing operation must not reach the approval reader or writer")

    def retry(candidate):
        return apply_approved_case_update(restarted, **context, call=candidate,
                                          read_approval=unexpected, write_case=unexpected)

    assert retry(call) == result
    assert result.case_revision == call.expected_case_revision + 1
    assert result.operation_id != call.client_operation_id
    for change in ({"proposal_id": uuid4()}, {"expected_case_revision": 2}):
        with pytest.raises(CaseOperationConflict, match="Operation key already used"):
            retry(call.model_copy(update=change))
    with pytest.raises(CaseOperationConflict, match="Proposal or case revision already applied"):
        retry(call.model_copy(update={"client_operation_id": uuid4()}))
    with pytest.raises(ValidationError):
        type(call).model_validate({**call.model_dump(), "expected_case_revision": 2**63 - 1})

    with pytest.raises(ToolAccessDenied):
        apply_approved_case_update(restarted, **{**context, "principal": BOB}, call=call,
                                   read_approval=unexpected, write_case=unexpected)
    with restarted() as db:
        assert db.get(CaseIntake, str(call.case_id)).facts == {"move_in_date": "2026-11-18"}
        assert db.get(AgentCaseOperation, str(result.operation_id)).client_operation_id == str(call.client_operation_id)


def test_another_run_cannot_claim_the_same_case_revision(approved_update):
    factory, context, call, approval = approved_update
    with factory.begin() as db:
        other_thread = create_thread(db, principal=ALICE)
        assert link_case_to_thread(db, principal=ALICE, thread_id=other_thread, case_id=call.case_id)
        conflicting_run = _run(db, other_thread, call.case_id)
    other, competing_call, competing_approval = _pending(factory, conflicting_run, call.case_id)
    apply_approved_case_update(factory, **context, call=call,
                               read_approval=lambda *_: approval, write_case=_write_intake)
    with pytest.raises(CaseOperationConflict, match="case revision already applied"):
        apply_approved_case_update(factory, **other, call=competing_call,
                                   read_approval=lambda *_: competing_approval,
                                   write_case=lambda *_: pytest.fail("revision was already consumed"))


@pytest.mark.parametrize("interrupted", [True, False])
def test_failed_write_rolls_back_case_and_receipt_before_retry(approved_update, interrupted):
    factory, context, call, approval = approved_update

    def interrupted_write(db, proposal):
        _write_intake(db, proposal)
        if interrupted:
            raise RuntimeError("synthetic interruption after flush")
        return proposal.expected_case_revision

    with pytest.raises(RuntimeError if interrupted else CaseOperationConflict):
        apply_approved_case_update(factory, **context, call=call,
                                   read_approval=lambda *_: approval, write_case=interrupted_write)
    with factory() as db:
        assert db.get(CaseIntake, str(call.case_id)) is None
        assert db.scalars(select(AgentCaseOperation)).all() == []
    result = apply_approved_case_update(factory, **context, call=call,
                                        read_approval=lambda *_: approval, write_case=_write_intake)
    with factory() as db:
        assert db.get(AgentCaseOperation, str(result.operation_id)) is not None


@pytest.mark.skipif(os.getenv("RUN_POSTGRES_SMOKE") != "1", reason="requires migrated disposable PostgreSQL")
@pytest.mark.parametrize("same_run", [True, False])
def test_concurrent_retries_and_case_revision_collisions(same_run):
    engine = create_engine(os.environ["DATABASE_URL"], pool_timeout=15)
    factory = sessionmaker(bind=engine)
    case_id = uuid4()
    scopes = []
    thread_ids = []
    try:
        with factory.begin() as db:
            db.add(CaseRecord(id=str(case_id), owner_subject=ALICE.subject))
            for _ in range(1 if same_run else 2):
                thread_id = create_thread(db, principal=ALICE)
                thread_ids.append(thread_id)
                assert link_case_to_thread(db, principal=ALICE, thread_id=thread_id, case_id=case_id)
                scopes.append(_run(db, thread_id, case_id))
        requests = [_pending(factory, scope, case_id) for scope in scopes]
        ready = Barrier(2, timeout=10)
        writes = []

        def write(db, proposal):
            writes.append(proposal.proposal_id)
            return _write_intake(db, proposal)

        def apply(request):
            context, call, approval = request
            ready.wait()
            try:
                return apply_approved_case_update(factory, **context, call=call,
                                                  read_approval=lambda *_: approval, write_case=write)
            except CaseOperationConflict:
                return None

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(apply, requests * 2 if same_run else requests))
        assert len(writes) == 1
        if same_run:
            assert results[0] is not None and results[0] == results[1]
        else:
            assert sum(result is not None for result in results) == 1
        with factory() as db:
            receipts = db.scalars(select(AgentCaseOperation).where(AgentCaseOperation.case_id == str(case_id))).all()
            assert len(receipts) == 1 and receipts[0].case_revision == 4
            assert db.get(CaseIntake, str(case_id)).facts == {"move_in_date": "2026-11-18"}
    finally:
        try:
            with factory.begin() as db:
                if case := db.get(CaseRecord, str(case_id)):
                    db.delete(case)
                for thread_id in thread_ids:
                    if thread := db.get(AgentThread, str(thread_id)):
                        db.delete(thread)
        finally:
            engine.dispose()
