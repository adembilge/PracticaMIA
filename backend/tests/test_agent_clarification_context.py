"""Use confirmed case context and authorized synthetic document results before asking."""

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from app.agent.candidate_resolution import choose_candidate_step
from app.agent.case_context import WorkerCaseContext
from app.agent.checkpoints import CheckpointState, submit_clarification_reply
from app.agent.contract import AnswerResult, ClarificationReply, DocumentObservation, NextAction, SendMessage
from app.agent.reconnect_router import build_reconnect_router
from app.agent.run_events import read_run_events
from app.agent.run_requests import StoredMessage, accept_message
from app.agent.threads import create_thread, link_case_to_thread
from app.agent.worker import RequestClarification, run_worker_step
from app.cases.intake_schemas import IntakeFacts
from app.knowledge.service_areas import CaseLocation, EffectivePeriod
from app.private_documents.model import PrivateCaseDocument
from app.rules.engine import JURISDICTION, PROCEDURE
from test_agent_run_requests import ALICE
from test_private_document_intelligence import FACTS, prepare_case, review_payload, sample_pdf, upload
from test_private_documents import document_client, enabled_settings  # noqa: F401
from test_service_areas import TRUSTED, area


STATE = CheckpointState(
    next_node="choose_next_step", intent="find_procedure", procedure_candidates=[PROCEDURE],
    missing_fields=["procedure_location"],
)
ASSIGNMENT = area(procedure_id=PROCEDURE, unit_ids=(JURISDICTION,))
ASSIGNMENT_REQUIRING_DATE = replace(
    ASSIGNMENT,
    effective_period=EffectivePeriod("move_in_date", effective_from=date(2026, 1, 1)),
    required_circumstances=(("housing_basis", "registered_private_rental"),),
)
INPUTS = {
    "case_locations": {}, "confirmed_dates": {}, "confirmed_circumstances": {},
    "assignments": (ASSIGNMENT_REQUIRING_DATE,), "trusted_passage_ids": TRUSTED, "reviewed_labels": {},
}


def test_confirmed_intake_supplies_applicable_destination_date_and_housing():
    case_id = uuid4()
    case = WorkerCaseContext(case_id, IntakeFacts(**FACTS), None, ())
    result = choose_candidate_step(
        StoredMessage("Residence change", "en", case_id, case_context=case), STATE, **INPUTS,
    )
    assert result.next_node == "verify_and_respond"
    assert result.missing_fields == []

    mismatched = choose_candidate_step(
        StoredMessage("Residence change", "en", uuid4(), case_context=case), STATE, **INPUTS,
    )
    assert isinstance(mismatched, RequestClarification)
    assert mismatched.question.missing_fields == ["destination", "move_in_date", "housing_basis"]


@pytest.mark.parametrize(("language", "text", "phrase"), [
    ("en", "I moved in on 2026-11-05.", "you gave in your message"),
    ("it", "Mi sono trasferita il 05/11/2026.", "hai indicato nel messaggio"),
    ("en", "I did not move in on 2026-11-05.", "On what date did you move in?"),
    ("en", "I moved in on 2026-02-30.", "On what date did you move in?"),
])
def test_message_dates_change_the_question_only_for_explicit_valid_statements(language, text, phrase):
    result = choose_candidate_step(
        StoredMessage(text, language, None), STATE, **(INPUTS | {
            "case_locations": {"destination": CaseLocation(municipality_id=JURISDICTION, confirmed=True)},
            "confirmed_circumstances": {"housing_basis": "registered_private_rental"},
        }),
    )
    assert isinstance(result, RequestClarification)
    assert result.question.missing_fields == ["move_in_date"]
    assert phrase in result.question.text
    assert "2026" not in result.question.text


def test_message_destination_requires_confirmation_even_when_some_city_names_were_extracted():
    result = choose_candidate_step(
        StoredMessage("Mi trasferisco a Milano.", "it", None),
        STATE, **(INPUTS | {"assignments": (ASSIGNMENT,)}),
    )
    assert isinstance(result, RequestClarification)
    assert result.question.missing_fields == ["destination"]
    assert "hai indicato nel messaggio" in result.question.text


def test_message_conflicts_with_saved_date_without_mutating_it():
    case_id = uuid4()
    case = WorkerCaseContext(case_id, IntakeFacts(**FACTS), None, ())
    result = choose_candidate_step(
        StoredMessage("Move-in date: 2026-11-06", "en", case_id, case_context=case),
        STATE, **INPUTS,
    )
    assert isinstance(result, RequestClarification)
    assert result.question.missing_fields == ["move_in_date"]
    assert "conflicting information" in result.question.text
    assert case.user_confirmed_facts.move_in_date == FACTS["move_in_date"]


@pytest.mark.parametrize(("scenario", "document_status", "phrase"), [
    ("pending", "needs_review", "review the move-in date in your document"),
    ("reviewed", "reviewed", "you reviewed in your document"),
    ("conflict", "conflict", "conflicting information"),
    ("expired", None, "On what date did you move in?"),
    ("disabled", None, "On what date did you move in?"),
    ("corrupt", None, "On what date did you move in?"),
    ("other-case", None, "On what date did you move in?"),
    ("removed", "needs_review", "review the move-in date in your document"),
])
def test_worker_checks_only_accessible_private_document_reviews(
    document_client, auth_headers, scenario, document_status, phrase,
):
    client = document_client
    headers = auth_headers("alice")
    case_id = prepare_case(client, headers)
    case_path = f"/api/v1/cases/{case_id}"
    saved_facts = FACTS.copy()
    if scenario != "conflict":
        saved_facts.pop("move_in_date")
        assert client.put(case_path + "/intake", headers=headers, json={
            "facts": saved_facts, "confirm": True,
        }).status_code == 200

    document_case = prepare_case(client, headers) if scenario == "other-case" else case_id
    document_id = upload(client, headers, document_case, sample_pdf("Move-in date: 2026-11-06"))
    path = f"/api/v1/cases/{document_case}/private-documents/{document_id}/intelligence"
    response = client.post(path + "/extract", headers=headers)
    assert response.status_code == 200
    if scenario not in {"pending", "removed"}:
        assert client.put(path + "/review", headers=headers, json=review_payload(response.json())).status_code == 200

    factory = client.app.state.session_factory
    key = b"\x5a" * 32
    with factory.begin() as db:
        document = db.get(PrivateCaseDocument, document_id)
        if scenario == "expired":
            document.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        elif scenario == "corrupt":
            document.review_ciphertext = b"x" * 40
        thread_id = create_thread(db, principal=ALICE)
        assert link_case_to_thread(db, thread_id=thread_id, case_id=UUID(case_id), principal=ALICE)
        run = accept_message(
            db, thread_id=thread_id, principal=ALICE, key=key,
            message=SendMessage(client_message_id=uuid4(), text="Residence change", language="en", case_id=UUID(case_id)),
        )

    context = {"thread_id": thread_id, "run_id": run.run_id, "principal": ALICE, "key": key}
    settings = None if scenario == "disabled" else enabled_settings()

    def start(message, _state):
        assert message.case_context.document_fields == {}
        return STATE

    assert run_worker_step(factory, **context, document_settings=settings, execute=start).status == "running"

    def choose(message, state):
        fields = {"move_in_date": document_status} if document_status else {}
        assert message.case_context.document_fields == fields
        return choose_candidate_step(message, state, **INPUTS)

    paused = run_worker_step(factory, **context, document_settings=settings, execute=choose)
    assert paused.status == "waiting_for_information"
    with factory.begin() as db:
        [event] = read_run_events(db, **context, after_seq=paused.last_event_seq - 1).events
    assert event.question.missing_fields == ["move_in_date"]
    assert phrase in event.question.text
    assert "2026-11-06" not in event.question.text
    assert document_id not in event.question.text

    with factory.begin() as db:
        if scenario == "removed":
            db.delete(db.get(PrivateCaseDocument, document_id))
        submit_clarification_reply(
            db, **context, question_id=event.question.question_id,
            reply=ClarificationReply(
                client_reply_id=uuid4(), expected_run_revision=paused.run_revision, disposition="skip",
            ),
        )
    completed = run_worker_step(
        factory, **context, document_settings=settings,
        execute=lambda *_: AnswerResult(
            explanation="Synthetic case still needs follow-up.",
            verification_status="insufficient_evidence",
            missing_information=["move_in_date"],
            next_action=NextAction(label="Review the case", operation="provide_information"),
            document_observations=[DocumentObservation(field_id="housing_basis", status="reviewed")],
        ),
    )
    expected = (
        [{"field_id": "move_in_date", "status": document_status, "origin": "user_document"}]
        if document_status and scenario != "removed" else []
    )
    client.app.include_router(build_reconnect_router(key=key))
    url = f"/api/v1/agent/threads/{thread_id}/runs/{run.run_id}"
    snapshot = client.get(url, headers=headers)
    assert snapshot.status_code == 200
    body = snapshot.json()["result"]
    assert body["document_observations"] == expected
    assert body["next_action"]["origin"] == "agent_proposal"
    assert body["verification_status"] == "insufficient_evidence"
    assert body["claims"] == body["citations"] == []
    assert "2026-11-06" not in snapshot.text
    assert document_id not in snapshot.text
    replay = client.get(url + "/events", headers=headers, params={"after_seq": completed.last_event_seq - 1})
    assert replay.status_code == 200
    assert replay.json()["events"][0]["result"] == body
    assert client.get(url, headers=auth_headers("bob")).status_code == 404

    facts = client.get(case_path + "/intake", headers=headers).json()["facts"]
    assert facts.get("move_in_date") == saved_facts.get("move_in_date")
