"""The isolated outcome step uses reviewed synthetic assignments and worker events."""

from dataclasses import replace
from datetime import date, datetime, timezone
from functools import partial
from uuid import UUID, uuid4

import pytest

from app.agent.candidate_resolution import AssistanceContact, choose_candidate_step
from app.agent.checkpoints import CheckpointState, load_checkpoint, submit_clarification_reply
from app.agent.contract import AnswerResult, Citation, ClarificationReply
from app.agent.run_events import read_run_events
from app.agent.run_requests import StoredMessage
from app.agent.worker import RequestClarification, run_worker_step
from app.knowledge.service_areas import CaseLocation, EffectivePeriod
from test_agent_run_events import queued_run  # noqa: F401 - shared synthetic run fixture
from test_service_areas import TRUSTED, area


DESTINATION = CaseLocation(municipality_id="municipality-b", confirmed=True)
SERVICE = area()
CONFLICT = area(assignment_id="other-office", authority_id="authority-b")
OTHER_PROCEDURE = area(assignment_id="other-procedure", procedure_id="procedure-b")
STATE = CheckpointState(
    next_node="choose_next_step", intent="find_procedure", procedure_candidates=["procedure-a"],
)
SOURCE_VERSION = UUID("81c3124c-a91a-4588-ad62-40c4ef1a3521")
CONTACT_ID = f"{SOURCE_VERSION}:0001"
CONTACT = AssistanceContact(
    scope=area(assignment_id="assistance", authority_id="help-desk", evidence_ref=CONTACT_ID),
    citation=Citation(
        citation_id=CONTACT_ID, passage_id=CONTACT_ID, source_id="fictional-contact",
        source_version_id=SOURCE_VERSION, official_url="https://example.invalid/help",
        publisher="Fictional assistance desk", reviewed_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
        procedure_id="procedure-a", location_id="municipality-b",
    ),
)
INPUTS = {
    "case_locations": {"destination": DESTINATION},
    "confirmed_dates": {},
    "confirmed_circumstances": {},
    "assignments": (SERVICE,),
    "trusted_passage_ids": TRUSTED | {CONTACT_ID},
    "reviewed_labels": {
        "procedure-a": "Fictional residence registration",
        "procedure-b": "Fictional address correction",
        "authority-a": "Fictional registry",
        "authority-b": "Fictional records office",
    },
}


def choose(state=STATE, *, language="en", **changes):
    return choose_candidate_step(
        StoredMessage("Synthetic request", language, None), state, **(INPUTS | changes),
    )


def test_empty_search_asks_for_goal_without_guessing_location():
    state = STATE.model_copy(update={
        "procedure_candidates": [], "missing_fields": ["procedure", "procedure_location"],
    })
    result = choose(state, language="it", assistance_contacts=(CONTACT,))
    assert isinstance(result, RequestClarification)
    assert result.question.missing_fields == ["procedure"]
    assert result.question.text == "Per quale pratica ti serve aiuto?"
    assert result.resume_state == state


def test_procedure_collision_explains_reviewed_alternatives_and_accepts_a_free_text_goal():
    state = STATE.model_copy(update={"procedure_candidates": ["procedure-a", "procedure-b"]})
    result = choose(state, assignments=(SERVICE, OTHER_PROCEDURE))
    assert isinstance(result, RequestClarification)
    assert result.question.answer_shape == "free_text"
    assert result.question.missing_fields == ["procedure"]
    assert all(INPUTS["reviewed_labels"][item] in result.question.text for item in state.procedure_candidates)

    several_tasks = state.model_copy(update={"intent": "plan_multiple_tasks"})
    result = choose(several_tasks, assignments=(SERVICE, OTHER_PROCEDURE))
    assert result.next_node == "verify_and_respond"
    assert result.procedure_candidates == state.procedure_candidates


def test_one_question_uses_the_confirmed_case_and_relevant_missing_field():
    service = replace(
        SERVICE, effective_period=EffectivePeriod("filing_date", effective_from=date(2026, 4, 1)),
        required_circumstances=(("housing_basis", "owner"),),
    )
    state = STATE.model_copy(update={"missing_fields": ["procedure_location"]})
    result = choose(state, language="it", assignments=(service,), assistance_contacts=(CONTACT,))
    assert isinstance(result, RequestClarification)
    assert result.question.missing_fields == ["filing_date"]
    assert result.question.text == "Qual è la data di presentazione della pratica?"

    result = choose(state, assignments=(service,), confirmed_dates={"filing_date": date(2026, 4, 1)})
    assert isinstance(result, RequestClarification)
    assert result.question.missing_fields == ["housing_basis"]
    result = choose(state, assignments=(service,), confirmed_dates={"filing_date": date(2026, 4, 1)},
                    confirmed_circumstances={"housing_basis": "owner"})
    assert result.next_node == "verify_and_respond"
    assert result.missing_fields == []


def test_official_assistance_is_independent_of_authority_conflict():
    result = choose(assignments=(SERVICE, CONFLICT), assistance_contacts=(CONTACT,))
    assert isinstance(result, AnswerResult)
    assert result.verification_status == "conflicting_evidence"
    assert all(INPUTS["reviewed_labels"][item] in result.explanation for item in ("authority-a", "authority-b"))
    assert result.citations == [CONTACT.citation]
    assert result.official_channel.url == CONTACT.citation.official_url
    assert result.next_action.operation == "open_official_channel"

    empty = choose(assignments=(), assistance_contacts=(CONTACT,))
    assert empty.verification_status == "insufficient_evidence"
    assert empty.official_channel == result.official_channel


@pytest.mark.parametrize("changes", [
    {"trusted_passage_ids": TRUSTED},
    {"case_locations": {"current_position": DESTINATION}},
    {"case_locations": {"destination": replace(DESTINATION, confirmed=False)}},
    {"case_locations": {"destination": CaseLocation(municipality_id="another-municipality", confirmed=True)}},
    {"assistance_contacts": (replace(CONTACT, scope=replace(CONTACT.scope, approved_for_routing=False)),)},
    {"assistance_contacts": (replace(CONTACT, scope=replace(CONTACT.scope, active=False)),)},
    {"assistance_contacts": (replace(CONTACT, scope=replace(CONTACT.scope, evidence_ref="other")),)},
    {"assistance_contacts": (replace(CONTACT, scope=replace(CONTACT.scope, procedure_id="procedure-b")),)},
    {"assistance_contacts": (replace(CONTACT, scope=replace(CONTACT.scope, unit_ids=("municipality-b", "other"))),)},
    {"assistance_contacts": (replace(CONTACT, scope=replace(
        CONTACT.scope, required_circumstances=(("housing_basis", "owner"),),
    )),)},
    {"assistance_contacts": (CONTACT, replace(CONTACT, scope=replace(CONTACT.scope, authority_id="other-help-desk")))},
])
def test_unverified_inapplicable_or_conflicting_contact_is_never_published(changes):
    result = choose(**({"assignments": (), "assistance_contacts": (CONTACT,)} | changes))
    assert isinstance(result, AnswerResult)
    assert result.verification_status == "insufficient_evidence"
    assert result.official_channel is None
    assert result.next_action is None
    assert result.citations == []


def test_worker_persists_question_and_does_not_repeat_it_or_treat_reply_as_confirmed(queued_run):
    factory, context, _, _ = queued_run
    assert run_worker_step(factory, **context, execute=lambda *_: STATE).status == "running"
    step = partial(choose_candidate_step, **(INPUTS | {"case_locations": {}}))

    paused = run_worker_step(factory, **context, execute=step)
    assert paused.status == "waiting_for_information"
    with factory.begin() as db:
        [event] = read_run_events(db, **context, after_seq=paused.last_event_seq - 1).events
        question = event.question
        assert question.missing_fields == ["destination"]
        assert load_checkpoint(db, **context).state.pending_question_id == question.question_id
        submit_clarification_reply(
            db, **context, question_id=question.question_id,
            reply=ClarificationReply(
                client_reply_id=uuid4(), expected_run_revision=paused.run_revision, text="Fictional town",
            ),
        )

    finished = run_worker_step(factory, **context, execute=step)
    assert finished.status == "completed"
    assert finished.result.verification_status == "insufficient_evidence"
    assert finished.result.missing_information == ["destination"]
    assert finished.result.official_channel is None
