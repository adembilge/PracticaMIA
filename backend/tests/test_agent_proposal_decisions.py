"""Exercise decisions through the signed, isolated application transport."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from app.agent.contract import ProposalDecision
from app.agent.reconnect_router import build_reconnect_router
from app.agent.tool_execution import ToolExecutionDenied
from app.agent.tool_writes import apply_approved_case_update
from app.cases.intake_model import CaseIntake
from test_agent_run_requests import ALICE, KEY
from test_agent_tool_access import tool_run  # noqa: F401 - shared owned-run fixture
from test_agent_tool_execution import _save_pending
from test_agent_tool_writes import _write_intake


@pytest.fixture
def review(client, tool_run, request):
    scope, _, case_id, _, _ = tool_run
    factory = client.app.state.session_factory
    context = {**scope, "principal": ALICE, "key": KEY}
    expiry = timedelta(minutes=-5 if getattr(request, "param", False) else 5)
    event, call, approval = _save_pending(factory, context, case_id, datetime.now(timezone.utc) + expiry)
    client.app.include_router(build_reconnect_router(key=KEY))
    run_url = f"/api/v1/agent/threads/{event.thread_id}/runs/{event.run_id}"
    return context, run_url, event, call, approval


def _decision(snapshot, decision, **fields):
    return {
        "decision": decision, "expected_run_revision": snapshot["run_revision"],
        "expected_case_revision": snapshot["pending_proposal"]["expected_case_revision"],
        "client_decision_id": str(uuid4()), **fields,
    }


def test_valid_correction_gets_a_new_review_then_only_its_accepted_value_can_apply(client, auth_headers, review):
    context, run_url, old_event, old_call, approval = review
    owner = auth_headers("alice")
    first = client.get(run_url, headers=owner).json()
    original_url = f"{run_url}/proposals/{old_event.proposal.proposal_id}/decision"
    correction = _decision(first, "correct", corrected_value="2026-11-20")
    assert client.post(original_url, headers=auth_headers("bob"), json=correction).status_code == 404
    bad = client.post(original_url, headers=owner, json={**correction, "corrected_value": "2026-02-30"})
    assert bad.status_code == 422
    assert bad.json()["code"] == "invalid_proposal_value"
    assert "2026-02-30" not in bad.text
    stale = client.post(original_url, headers=owner, json={**correction, "expected_case_revision": 9})
    assert stale.status_code == 409
    assert client.get(run_url, headers=owner).json() == first
    corrected = client.post(original_url, headers=owner, json=correction)
    assert corrected.status_code == 200
    assert corrected.headers["Cache-Control"] == "private, no-store"
    assert corrected.json()["decision"]["decision"] == "correct"
    second = client.get(run_url, headers=owner).json()
    proposal = second["pending_proposal"]
    assert proposal["proposal_id"] != str(old_event.proposal.proposal_id)
    assert proposal["field_id"] == old_event.proposal.field_id
    assert proposal["previous_value"] == old_event.proposal.previous_value
    assert proposal["proposed_value"] == "2026-11-20"
    assert second["approval_recorded"] is False
    assert client.post(original_url, headers=owner, json=correction).json() == corrected.json()
    assert client.post(original_url, headers=owner, json=_decision(second, "accept")).status_code == 409
    factory = client.app.state.session_factory

    def must_not_write(*_):
        pytest.fail("An unaccepted or replaced proposal must never reach the writer")

    new_id = UUID(proposal["proposal_id"])
    new_call = old_call.model_copy(update={"proposal_id": new_id})
    for call in (old_call, new_call):
        with pytest.raises(ToolExecutionDenied, match="Current user approval"):
            apply_approved_case_update(factory, **context, call=call,
                                       read_approval=must_not_write, write_case=must_not_write)
    url = f"{run_url}/proposals/{new_id}/decision"
    acceptance = _decision(second, "accept")
    accepted = client.post(url, headers=owner, json=acceptance)
    assert accepted.status_code == 200
    assert client.post(url, headers=owner, json=acceptance).json() == accepted.json()
    final = client.get(run_url, headers=owner).json()
    assert final["approval_recorded"] is True
    assert final["pending_proposal"] is None
    assert client.post(url, headers=owner, json={**acceptance, "decision": "reject"}).status_code == 409
    recorded = replace(
        approval, proposal_id=new_id, proposal_event_seq=second["last_event_seq"],
        decision=ProposalDecision.model_validate(accepted.json()["decision"]),
    )
    with factory() as db:
        assert db.get(CaseIntake, str(new_call.case_id)) is None
    wrong_decision = replace(recorded, decision=recorded.decision.model_copy(update={"client_decision_id": uuid4()}))
    with pytest.raises(ToolExecutionDenied):
        apply_approved_case_update(factory, **context, call=new_call,
                                   read_approval=lambda *_: wrong_decision, write_case=must_not_write)
    receipt = apply_approved_case_update(factory, **context, call=new_call,
                                         read_approval=lambda *_: recorded, write_case=_write_intake)
    assert receipt.case_revision == old_call.expected_case_revision + 1
    with factory() as db:
        assert db.get(CaseIntake, str(new_call.case_id)).facts == {"move_in_date": "2026-11-20"}


@pytest.mark.parametrize("decision", ["reject", "cancel"])
def test_declining_closes_review_and_blocks_the_writer(client, auth_headers, review, decision):
    context, run_url, event, call, approval = review
    owner = auth_headers("alice")
    before = client.get(run_url, headers=owner).json()
    url = f"{run_url}/proposals/{event.proposal.proposal_id}/decision"
    payload = _decision(before, decision)
    saved = client.post(url, headers=owner, json=payload)
    assert saved.status_code == 200
    assert saved.json()["decision"]["decision"] == decision
    assert client.post(url, headers=owner, json=payload).json() == saved.json()
    assert client.post(url, headers=owner, json={**payload, "decision": "accept"}).status_code == 409
    run = client.get(run_url, headers=owner).json()
    assert run["status"] == "stopped"
    assert run["pending_proposal"] is None
    assert run["approval_recorded"] is False
    events = client.get(run_url + "/events", headers=owner).json()["events"]
    assert events[-2] == saved.json()
    assert events[-1]["committed_operation_ids"] == []
    factory = client.app.state.session_factory
    with pytest.raises(ToolExecutionDenied):
        apply_approved_case_update(
            factory, **context, call=call, read_approval=lambda *_: approval,
            write_case=lambda *_: pytest.fail("A declined proposal cannot apply"),
        )
    with factory() as db:
        assert db.get(CaseIntake, str(call.case_id)) is None


@pytest.mark.parametrize("review", [True], indirect=True)
def test_expired_proposal_can_be_cancelled_but_not_accepted(client, auth_headers, review):
    _, run_url, event, _, _ = review
    owner = auth_headers("alice")
    snapshot = client.get(run_url, headers=owner).json()
    url = f"{run_url}/proposals/{event.proposal.proposal_id}/decision"
    assert client.post(url, headers=owner, json=_decision(snapshot, "accept")).status_code == 409
    assert client.post(url, headers=owner, json=_decision(snapshot, "cancel")).status_code == 200
    assert client.get(run_url, headers=owner).json()["status"] == "stopped"
