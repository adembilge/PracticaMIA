"""Exercise proposal dependencies through a worker pause and an actual write transaction."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.agent.checkpoints import CheckpointState
from app.agent.contract import ApprovalProposal, SubmitProposalDecision
from app.agent.proposal_decisions import submit_proposal_decision
from app.agent.tool_contract import ApplyApprovedUpdate
from app.agent.tool_execution import ProposalOutdated, RecordedToolApproval
from app.agent.tool_writes import AgentCaseOperation, apply_approved_case_update
from app.agent.worker import RequestApproval, run_worker_step
from app.cases.intake_model import CaseIntake
from app.knowledge.review_service import revoke_version
from test_agent_run_requests import ALICE, KEY
from test_agent_tool_access import tool_run  # noqa: F401 - shared owned-run fixture
from test_agent_tool_execution import _save_pending
from test_agent_tool_writes import _write_intake
from test_case_intake import SCOPE
from test_knowledge_search import OTHER_HTML, _approve, _create, _search


@pytest.fixture
def worker_change(client, tool_run):
    scope, _, case_id, _, _ = tool_run
    factory = client.app.state.session_factory
    context = {**scope, "principal": ALICE, "key": KEY}
    proposal = ApprovalProposal(
        proposal_id=uuid4(), case_id=case_id, field_id="move_in_date", previous_value=None,
        proposed_value="2026-11-18", rationale="Synthetic change", expected_case_revision=3,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    return factory, context, proposal


def _review(factory, context, proposal, run_revision, decision, corrected_value=None):
    with factory.begin() as db:
        return submit_proposal_decision(
            db, **context, proposal_id=proposal.proposal_id,
            payload=SubmitProposalDecision(
                decision=decision, expected_run_revision=run_revision,
                expected_case_revision=proposal.expected_case_revision,
                client_decision_id=uuid4(), corrected_value=corrected_value,
            ),
        )


def _approve_change(worker_change, snapshot):
    factory, context, _ = worker_change
    proposal = snapshot.pending_proposal
    recorded = _review(factory, context, proposal, snapshot.run_revision, "accept")
    call = ApplyApprovedUpdate(
        tool="apply_approved_update", case_id=proposal.case_id, proposal_id=proposal.proposal_id,
        expected_case_revision=proposal.expected_case_revision, client_operation_id=uuid4(),
    )
    approval = RecordedToolApproval(
        actor_subject=ALICE.subject, thread_id=context["thread_id"], run_id=context["run_id"],
        case_id=call.case_id, proposal_event_seq=recorded.proposal_event_seq, proposal_id=call.proposal_id,
        current_case_revision=call.expected_case_revision, decision=recorded.decision,
    )
    return call, approval


@pytest.mark.parametrize("when", ["during_draft", "after_approval", "before_correction"])
def test_case_edit_with_unchanged_reported_revision_requires_a_new_review(
    client, auth_headers, worker_change, when,
):
    factory, context, proposal = worker_change
    headers = auth_headers("alice")
    url = f"/api/v1/conversations/tasks/{proposal.case_id}"
    assert client.patch(url + "/scope", json={"answers": SCOPE}, headers=headers).status_code == 200

    def edit_case():
        response = client.put(
            f"/api/v1/conversations/tasks/{proposal.case_id}/intake", headers=headers,
            json={"facts": {"move_in_date": "2026-11-15"}, "confirm": False},
        )
        assert response.status_code == 200

    def draft(*_):
        if when == "during_draft":
            edit_case()
        return RequestApproval(proposal, CheckpointState(next_node="verify_and_respond"))

    pending = run_worker_step(factory, **context, execute=draft)
    if when == "before_correction":
        edit_case()
        _review(factory, context, proposal, pending.run_revision, "correct", "2026-11-20")
        pending = run_worker_step(factory, **context, execute=lambda *_: pytest.fail("review must stay paused"))
        assert pending.pending_proposal.proposed_value == "2026-11-20"
    call, approval = _approve_change(worker_change, pending)
    if when == "after_approval":
        edit_case()

    with pytest.raises(ProposalOutdated, match="requires a new review"):
        apply_approved_case_update(
            factory, **context, call=call, read_approval=lambda *_: approval,
            write_case=lambda *_: pytest.fail("Case edit must stop the approved write"),
        )
    with factory() as db:
        assert db.get(CaseIntake, str(call.case_id)).facts == {"move_in_date": "2026-11-15"}
        assert db.scalars(select(AgentCaseOperation)).all() == []


@pytest.mark.parametrize("change", ["none", "revoke", "pending_revision", "replace"])
def test_approved_write_requires_the_exact_current_passages(client, auth_headers, worker_change, change):
    factory, context, proposal = worker_change
    version, digest = _create(client)
    _approve(client, version, digest)
    [passage] = _search(client, auth_headers("alice"), limit=1).json()["evidence"]
    retrieved = CheckpointState(next_node="verify_and_respond", evidence_ids=[passage["citation_id"]])
    run_worker_step(factory, **context, execute=lambda *_: retrieved)
    # Even when the resume state drops the old passage, the draft still consumed it.
    pending = run_worker_step(factory, **context, execute=lambda *_: RequestApproval(
        proposal, CheckpointState(next_node="verify_and_respond"),
    ))
    call, approval = _approve_change(worker_change, pending)

    if change == "none":
        result = apply_approved_case_update(
            factory, **context, call=call, read_approval=lambda *_: approval, write_case=_write_intake,
        )
        with factory() as db:
            assert db.get(AgentCaseOperation, str(result.operation_id)) is not None
            assert db.get(CaseIntake, str(call.case_id)).facts == {"move_in_date": "2026-11-18"}
        return
    if change == "revoke":
        with factory.begin() as db:
            revoke_version(
                db, version_id=version, expected_digest=digest,
                actor_subject="synthetic-reviewer", reason="Withdrawn test fixture",
            )
    else:
        replacement, replacement_digest = _create(client, html=OTHER_HTML)
        if change == "replace":
            _approve(client, replacement, replacement_digest)

    with pytest.raises(ProposalOutdated):
        apply_approved_case_update(
            factory, **context, call=call, read_approval=lambda *_: approval,
            write_case=lambda *_: pytest.fail("Stale evidence must block the writer"),
        )
    with factory() as db:
        assert db.get(CaseIntake, str(call.case_id)) is None
        assert db.scalars(select(AgentCaseOperation)).all() == []


def test_unknown_evidence_prevents_a_reviewable_proposal(worker_change):
    factory, context, proposal = worker_change
    state = CheckpointState(next_node="verify_and_respond", evidence_ids=[f"{uuid4()}:0001"])
    result = run_worker_step(factory, **context, execute=lambda *_: RequestApproval(proposal, state))
    assert result.status == "completed"
    assert result.result.verification_status == "insufficient_evidence"
    assert result.pending_proposal is None


def test_unbound_historical_approval_cannot_write(worker_change):
    factory, context, proposal = worker_change
    _, call, approval = _save_pending(
        factory, context, proposal.case_id, proposal.expires_at, bind_freshness=False,
    )
    with pytest.raises(ProposalOutdated):
        apply_approved_case_update(
            factory, **context, call=call, read_approval=lambda *_: approval,
            write_case=lambda *_: pytest.fail("The earlier proposal has no dependency snapshot"),
        )
