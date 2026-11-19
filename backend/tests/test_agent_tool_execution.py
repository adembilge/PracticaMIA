from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.agent.checkpoints import CheckpointState, load_checkpoint, save_checkpoint, stop_run
from app.agent.contract import ApprovalProposal, ApprovalRequested, ProgressUpdated, ProposalDecision
from app.agent.proposal_freshness import (
    ProposalFreshness, case_proposal_fingerprint, case_snapshot_query, proposal_evidence_fingerprint,
)
from app.agent.tool_access import ToolAccessDenied
from app.agent.tool_contract import ApplyApprovedUpdate, MarkChecklistItem, ProposeCaseUpdate, ReadCaseContext
from app.agent.tool_execution import RecordedToolApproval, ToolExecutionDenied, check_tool_execution
from app.agent.worker import run_worker_step
from app.cases.intake_model import CaseIntake
from test_agent_run_requests import ALICE, BOB, KEY
from test_agent_tool_access import tool_run  # noqa: F401 - shared owned-run fixture


def _start(factory, context):
    return run_worker_step(factory, **context, execute=lambda *_: CheckpointState(next_node="choose_next_step"))


def test_read_and_draft_tools_require_a_running_owned_run(client, tool_run):
    context, _, case_id, _, _ = tool_run
    context = {**context, "principal": ALICE, "key": KEY}
    factory = client.app.state.session_factory
    read = ReadCaseContext(tool="read_case_context", case_id=case_id)
    draft = ProposeCaseUpdate(
        tool="propose_case_update", case_id=case_id, expected_case_revision=1, rationale="Fixture review",
        change=MarkChecklistItem(kind="mark_checklist_item", item_id="fixture-step", reviewed=True),
    )

    with factory() as db:
        for call in (read, draft):
            with pytest.raises(ToolExecutionDenied, match="require a running run"):
                check_tool_execution(db, **context, call=call)
    running = _start(factory, context)
    with factory.begin() as db:
        for call in (read, draft):
            assert check_tool_execution(db, **context, call=call) is None
        with pytest.raises(ToolAccessDenied, match="Tool scope unavailable"):
            check_tool_execution(db, **{**context, "principal": BOB}, call=read)
        assert stop_run(db, **context, expected_run_revision=running.run_revision).status == "stopped"
    with factory() as db, pytest.raises(ToolExecutionDenied, match="require a running run"):
        check_tool_execution(db, **context, call=read)


def _save_pending(factory, context, case_id, expires_at, *, bind_freshness=True):
    running = _start(factory, context)
    proposal = ApprovalProposal(
        proposal_id=uuid4(), case_id=case_id, field_id="move_in_date", previous_value=None,
        proposed_value="2026-11-18", rationale="Confirm the move-in date",
        expected_case_revision=3, expires_at=expires_at,
    )
    event = ApprovalRequested(
        schema_version=1, thread_id=context["thread_id"], run_id=context["run_id"],
        event_seq=running.last_event_seq + 1, occurred_at=datetime.now(timezone.utc),
        type="approval.requested", proposal=proposal,
    )
    with factory.begin() as db:
        saved = load_checkpoint(db, **context)
        freshness = None
        if bind_freshness:
            snapshot = db.execute(case_snapshot_query(str(case_id), context["principal"].subject)).one()
            freshness = ProposalFreshness(
                case_fingerprint=case_proposal_fingerprint(*snapshot), passage_ids=[],
                evidence_fingerprint=proposal_evidence_fingerprint(db, []),
            )
        save_checkpoint(db, **context, expected_revision=saved.revision, expected_event_seq=saved.event_seq,
                        state=saved.state.model_copy(update={
                            "pending_proposal_id": proposal.proposal_id, "proposal_freshness": freshness,
                        }), event=event)
    call = ApplyApprovedUpdate(
        tool="apply_approved_update", case_id=case_id, proposal_id=proposal.proposal_id,
        expected_case_revision=proposal.expected_case_revision, client_operation_id=uuid4(),
    )
    approval = RecordedToolApproval(
        actor_subject=ALICE.subject, thread_id=event.thread_id, run_id=event.run_id, case_id=case_id,
        proposal_event_seq=event.event_seq, proposal_id=proposal.proposal_id, current_case_revision=3,
        decision=ProposalDecision(decision="accept", expected_case_revision=3, client_decision_id=uuid4()),
    )
    return event, call, approval


def test_writes_require_server_approval_bound_to_exact_proposal_and_current_revision(client, tool_run):
    context, _, case_id, other_case, _ = tool_run
    context = {**context, "principal": ALICE, "key": KEY}
    factory = client.app.state.session_factory
    event, call, approval = _save_pending(factory, context, case_id, datetime.now(timezone.utc) + timedelta(minutes=5))

    with pytest.raises(ValidationError, match="extra_forbidden"):
        ApplyApprovedUpdate.model_validate({**call.model_dump(), "approved": True})

    def no_decision(*_):
        return None

    def never_load(*_):
        pytest.fail("a different proposal or revision must not reach the decision store")

    with factory.begin() as db:
        for reader in (None, no_decision):
            with pytest.raises(ToolExecutionDenied, match="Current user approval is required"):
                check_tool_execution(db, **context, call=call, read_approval=reader)
        for override in ({"proposal_id": uuid4()}, {"expected_case_revision": 2}):
            with pytest.raises(ToolExecutionDenied, match="Current user approval is required"):
                check_tool_execution(db, **context, call=call.model_copy(update=override), read_approval=never_load)

        wrong_bindings = (
            {"actor_subject": BOB.subject}, {"thread_id": uuid4()}, {"run_id": uuid4()}, {"case_id": other_case},
            {"proposal_event_seq": event.event_seq - 1}, {"proposal_id": uuid4()}, {"current_case_revision": 4},
        )
        wrong_decisions = (
            {"decision": "reject"}, {"decision": "cancel"}, {"expected_case_revision": 2},
            {"decision": "correct", "corrected_value": "2026-11-19"}, {"corrected_value": "2026-11-19"},
        )
        stale = [replace(approval, **binding) for binding in wrong_bindings]
        stale.extend(replace(approval, decision=approval.decision.model_copy(update=change))
                     for change in wrong_decisions)
        for recorded in stale:
            with pytest.raises(ToolExecutionDenied, match="Current user approval is required"):
                check_tool_execution(db, **context, call=call, read_approval=lambda *_: recorded)

        def read_approval(session, run_id, proposal_id):
            assert session is db
            assert (run_id, proposal_id) == (event.run_id, event.proposal.proposal_id)
            return approval

        assert check_tool_execution(db, **context, call=call, read_approval=read_approval) == event.proposal
        assert db.get(CaseIntake, str(case_id)) is None


@pytest.mark.parametrize("expired", [True, False])
def test_expired_proposal_or_advanced_journal_cannot_be_applied(client, tool_run, expired):
    context, _, case_id, _, _ = tool_run
    context = {**context, "principal": ALICE, "key": KEY}
    factory = client.app.state.session_factory
    expiry = datetime.now(timezone.utc) + timedelta(minutes=-5 if expired else 5)
    event, call, approval = _save_pending(factory, context, case_id, expiry)
    if not expired:
        progress = ProgressUpdated(
            schema_version=1, thread_id=event.thread_id, run_id=event.run_id,
            event_seq=event.event_seq + 1, occurred_at=event.occurred_at,
            type="progress.updated", stage="fixture", text="The run advanced beyond the proposal boundary.",
        )
        with factory.begin() as db:
            saved = load_checkpoint(db, **context)
            save_checkpoint(db, **context, expected_revision=saved.revision, expected_event_seq=saved.event_seq,
                            state=saved.state, event=progress)
    with factory() as db, pytest.raises(ToolExecutionDenied, match="Current user approval is required"):
        check_tool_execution(db, **context, call=call, read_approval=lambda *_: approval)
