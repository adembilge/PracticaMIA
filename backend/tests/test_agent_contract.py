"""Synthetic Phase 4 wire fixtures; no runtime, approval, or live source access."""

from copy import deepcopy
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.agent.contract import (
    AnswerResult, ClarificationReply, EventPage, ProposalDecision, RunSnapshot, SendMessage, StopRun,
    agent_event_adapter,
)


THREAD = "50000000-0000-4000-8000-000000000001"
RUN = "50000000-0000-4000-8000-000000000002"
CASE = "50000000-0000-4000-8000-000000000003"
MESSAGE = "50000000-0000-4000-8000-000000000004"
QUESTION = "50000000-0000-4000-8000-000000000005"
PROPOSAL = "50000000-0000-4000-8000-000000000006"
SOURCE_VERSION = "50000000-0000-4000-8000-000000000007"
PASSAGE = f"{SOURCE_VERSION}:0003"
TIMESTAMP = "2026-11-18T10:00:00Z"
MESSAGE_BODY = {
    "client_message_id": MESSAGE, "text": "Where can I find an official source?",
    "language": "en", "case_id": CASE, "expected_thread_revision": 1,
}
CITATION = {
    "citation_id": PASSAGE, "source_id": "fictional-source",
    "source_version_id": SOURCE_VERSION, "passage_id": PASSAGE,
    "official_url": "https://example.invalid/source",
    "publisher": "Fictional publisher", "reviewed_at": TIMESTAMP,
    "procedure_id": "fictional-procedure", "location_id": "fictional-area",
}
ANSWER = {
    "explanation": "A separately reviewed source would appear here.",
    "verification_status": "verified",
    "official_channel": {"label": "Example route", "url": "https://example.invalid/channel"},
    "next_action": {"label": "Open the channel", "operation": "open_official_channel"},
    "citations": [CITATION],
}


def event(kind, seq, **payload):
    return {
        "schema_version": 1, "thread_id": THREAD, "run_id": RUN,
        "event_seq": seq, "type": kind, "occurred_at": TIMESTAMP, **payload,
    }


def test_message_fixture_preserves_retry_identifier_and_body():
    first = SendMessage.model_validate(MESSAGE_BODY)
    assert SendMessage.model_validate_json(first.model_dump_json()) == first

    reused = SendMessage.model_validate({**MESSAGE_BODY, "text": "A different question"})
    assert first.client_message_id == reused.client_message_id == UUID(MESSAGE)
    assert first.text != reused.text
    # Persisted deduplication and changed-body conflict require the runtime.


@pytest.mark.parametrize("changes", [
    {"text": "   "}, {"text": "x" * 2001}, {"principal": "client-chosen"},
    {"case_id": "invalid"}, {"expected_thread_revision": "1"}, {"language": "fr"},
])
def test_invalid_message_data_is_rejected(changes):
    with pytest.raises(ValidationError):
        SendMessage.model_validate({**MESSAGE_BODY, **changes})


def test_reply_requires_bounded_text_and_a_valid_event_revision():
    body = {"client_reply_id": MESSAGE, "expected_run_revision": 4, "text": " Area A "}
    assert ClarificationReply.model_validate(body).text == "Area A"
    for invalid in ({"text": " "}, {"text": "x" * 2001}, {"expected_run_revision": 2**31}):
        with pytest.raises(ValidationError):
            ClarificationReply.model_validate({**body, **invalid})


@pytest.mark.parametrize("fixture", [
    event("run.started", 1, client_message_id=MESSAGE),
    event("progress.updated", 2, stage="looking_up_context", text="Checking the case"),
    event("question.requested", 3, question={
        "question_id": QUESTION, "text": "Which area applies?", "answer_shape": "single_choice",
        "options": ["Area A", "Area B"], "missing_fields": ["location"],
    }),
    event("question.answered", 4, question_id=QUESTION, client_reply_id=MESSAGE, text="Area A"),
    event("approval.requested", 4, proposal={
        "proposal_id": PROPOSAL, "case_id": CASE, "field_id": "location",
        "previous_value": None, "proposed_value": "Area A", "rationale": "User entered the value",
        "expected_case_revision": 1, "expires_at": TIMESTAMP,
    }),
    event("answer.completed", 5, result=ANSWER),
    event("run.failed", 5, code="catalogue_unavailable", retryable=True, recovery="retry_later"),
    event("run.stopped", 5, committed_operation_ids=[]),
])
def test_discriminated_event_round_trip(fixture):
    value = agent_event_adapter.validate_python(fixture)
    assert agent_event_adapter.validate_json(value.model_dump_json()) == value


@pytest.mark.parametrize("fixture", [
    event("model.reasoning", 2, text="Internal prompt"),
    event("progress.updated", 2, stage="search", text="Working", raw_tool_output="private"),
    event("question.requested", 2, question={
        "question_id": QUESTION, "text": "Which area applies?", "answer_shape": "free_text",
        "options": ["Area A"], "missing_fields": ["location"],
    }),
    event("question.requested", 2, question={
        "question_id": QUESTION, "text": "Which area applies?", "answer_shape": "single_choice",
        "options": ["Area A", " Area A "], "missing_fields": ["location"],
    }),
    {**event("run.started", 1, client_message_id=MESSAGE), "occurred_at": "2026-11-18T10:00:00"},
])
def test_unknown_private_or_invalid_event_data_is_rejected(fixture):
    with pytest.raises(ValidationError):
        agent_event_adapter.validate_python(fixture)


@pytest.mark.parametrize(("field", "value"), [
    ("citations", []), ("official_channel", None),
    ("next_action", {"label": "Submit", "operation": "government_submit"}),
])
def test_verified_answer_shape_failures(field, value):
    with pytest.raises(ValidationError):
        AnswerResult.model_validate({**ANSWER, field: value})


@pytest.mark.parametrize("changes", [
    {"citation_id": f"{SOURCE_VERSION}:0004"},
    {"source_version_id": MESSAGE},
    {"official_url": "http://example.invalid/source"},
    {"official_url": "https://name:password@example.invalid/source"},
])
def test_source_card_identity_and_url(changes):
    response = deepcopy(ANSWER)
    response["citations"][0].update(changes)
    with pytest.raises(ValidationError):
        AnswerResult.model_validate(response)


def test_evidence_conflict_can_carry_candidate_citations():
    answer = AnswerResult.model_validate({
        "explanation": "The available evidence conflicts.",
        "verification_status": "conflicting_evidence",
        "citations": [CITATION],
        "missing_information": ["location"],
    })
    assert answer.citations[0].passage_id == PASSAGE
    assert answer.verification_status == "conflicting_evidence"


def test_reconnect_cursors_and_terminal_order():
    start = event("run.started", 1, client_message_id=MESSAGE)
    progress = event("progress.updated", 2, stage="lookup", text="Checking scope")
    stop = event("run.stopped", 3, committed_operation_ids=[])
    base = {"thread_id": THREAD, "run_id": RUN}
    first = EventPage.model_validate({
        **base, "after_seq": 0, "events": [start, progress], "last_event_seq": 2, "has_more": True,
    })
    last = EventPage.model_validate({
        **base, "after_seq": first.last_event_seq, "events": [stop],
        "last_event_seq": 3, "has_more": False,
    })
    assert [item.event_seq for item in first.events + last.events] == [1, 2, 3]
    empty = EventPage.model_validate({
        **base, "after_seq": 3, "events": [], "last_event_seq": 3, "has_more": False,
    })
    assert empty.events == []

    for changed in (
        {"events": [{**stop, "run_id": CASE}]},
        {"events": [{**stop, "event_seq": 4}]},
        {"last_event_seq": 4},
        {"has_more": True},
    ):
        with pytest.raises(ValidationError):
            EventPage.model_validate({
                **base, "after_seq": 2, "events": [stop], "last_event_seq": 3,
                "has_more": False, **changed,
            })


def test_stop_and_proposal_require_revisions_and_matching_payloads():
    assert StopRun.model_validate({"expected_run_revision": 1}).expected_run_revision == 1
    with pytest.raises(ValidationError):
        StopRun.model_validate({"expected_run_revision": 0})
    base = {"expected_case_revision": 2, "client_decision_id": MESSAGE}
    accepted = ProposalDecision.model_validate({**base, "decision": "accept"})
    corrected = ProposalDecision.model_validate({**base, "decision": "correct", "corrected_value": False})
    assert accepted.corrected_value is None
    assert corrected.corrected_value is False
    for changes in ({"decision": "correct"}, {"decision": "reject", "corrected_value": "B"}):
        with pytest.raises(ValidationError):
            ProposalDecision.model_validate({**base, **changes})


def test_run_snapshot_requires_completed_status_for_result():
    base = {"thread_id": THREAD, "run_id": RUN, "run_revision": 1, "last_event_seq": 3}
    completed = RunSnapshot.model_validate({**base, "status": "completed", "result": ANSWER})
    assert completed.result.citations[0].source_version_id == UUID(SOURCE_VERSION)
    for changed in ({"status": "completed"}, {"status": "running", "result": ANSWER}):
        with pytest.raises(ValidationError):
            RunSnapshot.model_validate({**base, **changed})
