"""Exercise actual LangGraph resumption through the isolated signed decision route."""

import json
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.agent import approval_resume
from app.agent.approval_graph import ApprovalGraphConflict, resume_approval
from app.agent.approval_resume import ApprovedCaseUpdates
from app.agent.case_operations import AgentCaseOperation
from app.agent.checkpoints import CheckpointState, load_checkpoint
from app.agent.contract import AnswerResult, ApprovalDecided
from app.agent.reconnect_router import build_reconnect_router
from app.agent.worker import RequestApproval, run_worker_step
from app.cases.intake_model import CaseIntake
from app.cases.model import CaseRecord
from app.knowledge.review_service import revoke_version
from test_agent_proposal_decisions import _decision
from test_agent_proposal_freshness import worker_change  # noqa: F401 - shared synthetic case
from test_agent_tool_access import tool_run  # noqa: F401 - dependency of worker_change
from test_agent_tool_writes import _write_intake
from test_knowledge_search import _approve, _create, _search


@pytest.fixture
def approval_run(client, auth_headers, worker_change):
    factory, context, proposal = worker_change
    pending = run_worker_step(
        factory, **context,
        execute=lambda *_: RequestApproval(proposal, CheckpointState(next_node="verify_and_respond")),
    )
    assert pending.pending_proposal == proposal
    restarted = sessionmaker(bind=factory.kw["bind"], expire_on_commit=False)
    client.app.state.session_factory = restarted
    base = f"/api/v1/agent/threads/{pending.thread_id}/runs/{pending.run_id}"
    return restarted, context, proposal, base, auth_headers("alice")


def test_owner_accepts_after_restart_and_the_same_run_continues(client, auth_headers, approval_run):
    factory, context, proposal, base, owner = approval_run
    writes = []

    def write(db, approved):
        writes.append(approved.proposal_id)
        return _write_intake(db, approved)

    updates = ApprovedCaseUpdates(lambda *_: 3, write)
    client.app.include_router(build_reconnect_router(key=context["key"], case_updates=updates))
    pending = client.get(base, headers=owner).json()
    correction = _decision(pending, "correct", corrected_value="2026-11-20")
    url = f"{base}/proposals/{proposal.proposal_id}/decision"
    assert client.post(url, headers=auth_headers("bob"), json=correction).status_code == 404
    assert client.post(url, headers=owner, json=correction).status_code == 200
    assert writes == []
    revised = client.get(base, headers=owner).json()
    new_id = revised["pending_proposal"]["proposal_id"]
    assert new_id != str(proposal.proposal_id)
    with factory() as db:
        checkpoint = load_checkpoint(db, **context)
        pause = checkpoint.state.approval_pause
        assert pause.thread_id == context["thread_id"]
        assert pause.run_id == context["run_id"]
        assert db.get(CaseIntake, str(proposal.case_id)) is None

    decision = _decision(revised, "accept")
    assert client.post(url, headers=owner, json=decision).status_code == 409
    accepted_url = f"{base}/proposals/{new_id}/decision"
    response = client.post(accepted_url, headers=owner, json=decision)
    assert response.status_code == 200
    accepted = ApprovalDecided.model_validate(response.json())
    with pytest.raises(ApprovalGraphConflict):
        resume_approval(pause, accepted.model_copy(update={"thread_id": uuid4()}))
    assert client.post(accepted_url, headers=owner, json=decision).json() == response.json()
    assert writes == [accepted.proposal_id]
    resumed = client.get(base, headers=owner).json()
    assert resumed["status"] == "running"
    assert resumed["run_id"] == revised["run_id"]
    applied = client.get(base + "/events", headers=owner).json()["events"][-1]
    assert applied["type"] == "approval.applied"
    assert applied["proposal_id"] == new_id
    with factory() as db:
        assert db.get(CaseIntake, str(proposal.case_id)).facts == {"move_in_date": "2026-11-20"}
        [receipt] = db.scalars(select(AgentCaseOperation)).all()
        assert (receipt.id, receipt.client_operation_id) == (applied["operation_id"], new_id)
        assert load_checkpoint(db, **context).state.approval_pause is None

    def next_step(message, state):
        assert state.next_node == "verify_and_respond"
        assert str(message.approval_applied.operation_id) == applied["operation_id"]
        return AnswerResult(explanation="The saved case was updated.", verification_status="insufficient_evidence")

    assert run_worker_step(factory, **context, execute=next_step).status == "completed"


def test_journal_failure_rolls_back_the_write_and_exact_decision_retry_recovers(
    client, approval_run, monkeypatch,
):
    factory, context, proposal, base, owner = approval_run
    updates = ApprovedCaseUpdates(lambda *_: 3, _write_intake)
    client.app.include_router(build_reconnect_router(key=context["key"], case_updates=updates))
    pending = client.get(base, headers=owner).json()
    decision = _decision(pending, "accept")
    url = f"{base}/proposals/{proposal.proposal_id}/decision"

    def interrupt_commit(*_, **__):
        raise RuntimeError("Synthetic interruption before the journal commit")

    with monkeypatch.context() as patch:
        patch.setattr(approval_resume, "save_checkpoint", interrupt_commit)
        with pytest.raises(RuntimeError, match="Synthetic interruption"):
            client.post(url, headers=owner, json=decision)
    with factory() as db:
        assert db.get(CaseIntake, str(proposal.case_id)) is None
        assert db.scalars(select(AgentCaseOperation)).all() == []
    assert client.get(base, headers=owner).json()["approval_recorded"]

    response = client.post(url, headers=owner, json=decision)
    assert response.status_code == 200
    resumed = client.get(base, headers=owner).json()
    with factory() as db:
        [receipt] = db.scalars(select(AgentCaseOperation.id)).all()
    stopped = client.post(base + "/stop", headers=owner, json={"expected_run_revision": resumed["run_revision"]})
    assert stopped.json()["status"] == "stopped"
    assert client.get(base + "/events", headers=owner).json()["events"][-1]["committed_operation_ids"] == [receipt]
    assert client.post(url, headers=owner, json=decision).json() == response.json()


@pytest.mark.parametrize("decision", ["reject", "cancel", "accept"])
def test_declined_or_stale_approval_cannot_write_through_resume(client, approval_run, decision):
    factory, context, proposal, base, owner = approval_run
    updates = ApprovedCaseUpdates(lambda *_: 3, lambda *_: pytest.fail("Unsafe write"))
    client.app.include_router(build_reconnect_router(key=context["key"], case_updates=updates))
    pending = client.get(base, headers=owner).json()
    if decision == "accept":
        with factory.begin() as db:
            db.get(CaseRecord, str(proposal.case_id)).status = "unsupported"
    url = f"{base}/proposals/{proposal.proposal_id}/decision"
    assert client.post(url, headers=owner, json=_decision(pending, decision)).status_code == 200
    last = client.get(base + "/events", headers=owner).json()["events"][-1]
    if decision == "accept":
        assert (last["type"], last["code"], last["recovery"]) == (
            "run.failed", "proposal_outdated", "review_proposal",
        )
    else:
        assert last["type"] == "run.stopped"
    with factory() as db:
        assert db.get(CaseIntake, str(proposal.case_id)) is None
        assert db.scalars(select(AgentCaseOperation)).all() == []


def test_stale_approval_log_records_the_bound_source_version_without_proposal_details(
    client, auth_headers, worker_change, caplog,
):
    factory, context, proposal = worker_change
    owner = auth_headers("alice")
    version, digest = _create(client)
    _approve(client, version, digest)
    [passage] = _search(client, owner, limit=1).json()["evidence"]
    resume_state = CheckpointState(
        next_node="verify_and_respond", intent="explain_form_field", evidence_ids=[passage["citation_id"]],
    )
    pending = run_worker_step(
        factory, **context, execute=lambda *_: RequestApproval(proposal, resume_state),
    )
    with factory.begin() as db:
        revoke_version(
            db, version_id=version, expected_digest=digest,
            actor_subject="synthetic-reviewer", reason="Withdrawn test fixture",
        )
    updates = ApprovedCaseUpdates(lambda *_: 3, lambda *_: pytest.fail("Unsafe write"))
    client.app.include_router(build_reconnect_router(key=context["key"], case_updates=updates))
    base = f"/api/v1/agent/threads/{pending.thread_id}/runs/{pending.run_id}"
    decision = _decision(client.get(base, headers=owner).json(), "accept")
    url = f"{base}/proposals/{proposal.proposal_id}/decision"
    first = client.post(url, headers=owner, json=decision)
    assert first.status_code == 200
    assert client.post(url, headers=owner, json=decision).json() == first.json()
    [record] = [row for row in caplog.records if row.name == "app.agent.diagnostics"]
    assert json.loads(record.getMessage()) == {
        "event": "agent_failure", "schema_version": 1, "code": "proposal_outdated",
        "stage": "resume_approval", "intent": "explain_form_field", "query_kind": None,
        "tool": "apply_approved_update", "source_version_ids": [version],
    }
    assert record.exc_info is None
    for private_value in (proposal.proposed_value, proposal.rationale, str(proposal.case_id), str(proposal.proposal_id)):
        assert private_value not in record.getMessage()
