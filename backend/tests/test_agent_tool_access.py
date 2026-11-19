from uuid import UUID, uuid4

import pytest
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.agent.catalogue_evidence import read_tool_evidence
from app.agent.contract import SendMessage
from app.agent.run_requests import accept_message
from app.agent.threads import create_thread, link_case_to_thread
from app.agent.tool_access import ToolAccessDenied, authorize_tool_call
from app.agent.tool_contract import (
    ApplyApprovedUpdate, CatalogueEvidence, CatalogueScope, FindEvidence, FindProcedure,
    MarkChecklistItem, OpenSourceDetails, ProposeCaseUpdate, ReadCaseContext,
)
from app.auth.tokens import Principal, get_principal
from app.cases.model import CaseRecord
from app.database import get_session
from app.rules.engine import JURISDICTION, PROCEDURE
from test_agent_run_requests import ALICE, BOB, KEY


SCOPE = CatalogueScope(procedure_id=PROCEDURE, location_id=JURISDICTION)


def _case(client, headers):
    response = client.post("/api/v1/cases", headers=headers, json={})
    assert response.status_code == 201
    return UUID(response.json()["id"])


def _run(db, thread_id, case_id):
    accepted = accept_message(db, principal=ALICE, thread_id=thread_id, key=KEY, message=SendMessage(
        client_message_id=uuid4(), text="Synthetic question", language="en", case_id=case_id,
    ))
    assert accepted.outcome == "accepted"
    return {"thread_id": thread_id, "run_id": accepted.run_id}


@pytest.fixture
def tool_run(client, auth_headers):
    case_id = _case(client, auth_headers())
    other_owned_case = _case(client, auth_headers())
    foreign_case = _case(client, auth_headers("bob"))
    factory = client.app.state.session_factory
    with factory.begin() as db:
        thread = create_thread(db, principal=ALICE)
        for owned_case in (case_id, other_owned_case):
            assert link_case_to_thread(db, principal=ALICE, thread_id=thread, case_id=owned_case)
        context = _run(db, thread, case_id)
        unscoped = _run(db, create_thread(db, principal=ALICE), None)
    return context, unscoped, case_id, other_owned_case, foreign_case


def test_all_tool_calls_require_the_acting_owner_and_exact_run_scope(client, auth_headers, tool_run):
    context, unscoped, case_id, other_owned_case, foreign_case = tool_run
    discovery = FindProcedure(tool="find_procedure", query="residenza", language="it")
    calls = (
        FindEvidence(tool="find_evidence", case_id=case_id, scope=SCOPE, query="residenza"),
        OpenSourceDetails(tool="open_source_details", case_id=case_id, scope=SCOPE, citation_id=f"{uuid4()}:0001"),
        ReadCaseContext(tool="read_case_context", case_id=case_id),
        ProposeCaseUpdate(
            tool="propose_case_update", case_id=case_id, expected_case_revision=1, rationale="Synthetic change",
            change=MarkChecklistItem(kind="mark_checklist_item", item_id="fixture-action", reviewed=True),
        ),
        ApplyApprovedUpdate(
            tool="apply_approved_update", case_id=case_id, proposal_id=uuid4(), expected_case_revision=1,
            client_operation_id=uuid4(),
        ),
    )

    factory = client.app.state.session_factory
    with factory() as db:
        for call in (discovery, *calls):
            authorize_tool_call(db, **context, principal=ALICE, call=call)
            with pytest.raises(ToolAccessDenied, match="^Tool scope unavailable$"):
                authorize_tool_call(db, **context, principal=BOB, call=call)
            with pytest.raises(ToolAccessDenied):
                authorize_tool_call(db, thread_id=unscoped["thread_id"], run_id=context["run_id"],
                                    principal=ALICE, call=call)
        authorize_tool_call(db, **unscoped, principal=ALICE, call=discovery)
        for call in calls:
            with pytest.raises(ToolAccessDenied):
                authorize_tool_call(db, **unscoped, principal=ALICE, call=call)
            for other_id in (other_owned_case, foreign_case, uuid4()):
                with pytest.raises(ToolAccessDenied, match="^Tool scope unavailable$"):
                    authorize_tool_call(db, **context, principal=ALICE, call=call.model_copy(
                        update={"case_id": other_id},
                    ))

    with factory.begin() as db:
        db.get(CaseRecord, str(case_id)).owner_subject = BOB.subject
    with factory() as db:
        for principal in (ALICE, BOB):
            with pytest.raises(ToolAccessDenied):
                authorize_tool_call(db, **context, principal=principal, call=calls[2])

    assert client.delete(f"/api/v1/cases/{case_id}", headers=auth_headers("bob")).status_code == 204
    with factory() as db, pytest.raises(ToolAccessDenied):
        authorize_tool_call(db, **context, principal=ALICE, call=discovery)


def test_evidence_tools_take_identity_from_the_verified_request(client, auth_headers, tool_run, monkeypatch):
    context, _, case_id, other_owned_case, foreign_case = tool_run
    reads = []

    def observe_read(db, *, thread_id, case_id, principal, **_):
        reads.append((thread_id, case_id, principal))
        return CatalogueEvidence(status="insufficient_evidence")

    monkeypatch.setattr("app.agent.catalogue_evidence.find_catalogue_evidence", observe_read)
    monkeypatch.setattr("app.agent.catalogue_evidence.resolve_catalogue_evidence", observe_read)

    # Mount this probe only in the signed synthetic app. The product adds no route.
    @client.app.post("/test/threads/{thread_id}/runs/{run_id}/evidence")
    def evidence_probe(
        thread_id: UUID, run_id: UUID, call: FindEvidence | OpenSourceDetails,
        principal: Principal = Depends(get_principal), db: Session = Depends(get_session),
    ) -> CatalogueEvidence:
        try:
            return read_tool_evidence(db, principal=principal, thread_id=thread_id, run_id=run_id, call=call)
        except ToolAccessDenied as exc:
            raise HTTPException(404, str(exc)) from None

    url = f"/test/threads/{context['thread_id']}/runs/{context['run_id']}/evidence"
    params = {"case_id": str(case_id), "scope": SCOPE.model_dump()}
    for args in (
        {**params, "tool": "find_evidence", "query": "residenza"},
        {**params, "tool": "open_source_details", "citation_id": f"{uuid4()}:0001"},
    ):
        for headers in ({}, auth_headers(overrides={"aud": "fixture-other-audience"})):
            assert client.post(url, headers=headers, json=args).status_code == 401
        for wrong_id in (other_owned_case, foreign_case, uuid4()):
            denied = client.post(url, headers=auth_headers(), json={**args, "case_id": str(wrong_id)})
            assert denied.status_code == 404
            assert denied.json() == {"detail": "Tool scope unavailable"}
        denied = client.post(url, headers=auth_headers("bob"), json=args)
        assert denied.status_code == 404
        assert denied.json() == {"detail": "Tool scope unavailable"}
        assert client.post(url, headers=auth_headers("bob"), json={**args, "principal": "alice"}).status_code == 422

    assert reads == []
    for tool in ({"tool": "find_evidence", "query": "residenza"},
                 {"tool": "open_source_details", "citation_id": f"{uuid4()}:0001"}):
        allowed = client.post(url, headers=auth_headers(), json={**params, **tool})
        assert allowed.status_code == 200
        assert allowed.json()["status"] == "insufficient_evidence"
    assert reads == [(context["thread_id"], case_id, ALICE)] * 2
