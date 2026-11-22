"""The isolated outcome step uses reviewed synthetic assignments and worker events."""

from dataclasses import replace
from datetime import date, datetime, timezone
from functools import partial
from uuid import UUID, uuid4

import pytest

from app.agent.answer_evidence import AnswerEvidenceScope, ClaimPassageSupport, ReviewedClaimSupport
from app.agent.candidate_resolution import AssistanceContact, choose_candidate_step
from app.agent.checkpoints import CheckpointState, load_checkpoint, submit_clarification_reply
from app.agent.contract import AnswerResult, Citation, ClarificationReply, OfficialChannel
from app.agent.run_events import read_run_events
from app.agent.run_requests import StoredMessage
from app.agent.worker import RequestClarification, run_worker_step
from app.knowledge.service_areas import CaseLocation, EffectivePeriod
from test_agent_answer_evidence import CONTACT_QUOTE, approved_citation  # noqa: F401 - shared registry fixture
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


def test_grouped_question_explains_joint_requirements_and_reuses_confirmed_facts():
    service = replace(
        SERVICE, effective_period=EffectivePeriod("filing_date", effective_from=date(2026, 4, 1)),
        required_circumstances=(("housing_basis", "owner"),),
    )
    state = STATE.model_copy(update={"missing_fields": ["procedure_location"]})
    result = choose(state, language="it", assignments=(service,), assistance_contacts=(CONTACT,))
    assert isinstance(result, RequestClarification)
    assert result.question.missing_fields == ["filing_date", "housing_basis"]
    assert result.question.text == (
        "Mi servono tutti questi dati per verificare se la procedura si applica. "
        "Puoi indicare la data di presentazione e il titolo di occupazione?"
    )

    result = choose(state, assignments=(service,), confirmed_dates={"filing_date": date(2026, 4, 1)})
    assert isinstance(result, RequestClarification)
    assert result.question.missing_fields == ["housing_basis"]
    assert result.question.answer_shape == "single_choice"
    assert "I own the home" in result.question.options
    result = choose(state, assignments=(service,), confirmed_dates={"filing_date": date(2026, 4, 1)},
                    confirmed_circumstances={"housing_basis": "owner"})
    assert result.next_node == "verify_and_respond"
    assert result.missing_fields == []


def test_housing_distinguishes_authorities_that_share_the_same_destination():
    rent = replace(SERVICE, required_circumstances=(("housing_basis", "rental"),))
    ownership = replace(CONFLICT, required_circumstances=(("housing_basis", "owner"),))
    withdrawn = area(assignment_id="withdrawn", authority_id="authority-c", evidence_ref="withdrawn-passage")
    for records in ((rent, ownership, withdrawn), (withdrawn, ownership, rent)):
        result = choose(case_locations={}, assignments=records)
        assert isinstance(result, RequestClarification)
        assert result.question.missing_fields == ["housing_basis"]


def test_filing_date_distinguishes_which_assignment_was_effective():
    before = replace(SERVICE, effective_period=EffectivePeriod("filing_date", effective_until=date(2026, 3, 31)))
    after = replace(CONFLICT, effective_period=EffectivePeriod("filing_date", effective_from=date(2026, 4, 1)))
    result = choose(case_locations={}, assignments=(before, after))
    assert isinstance(result, RequestClarification)
    assert result.question.missing_fields == ["filing_date"]
    assert result.question.answer_shape == "free_text"
    assert result.question.answer_format == "calendar_date"
    assert "YYYY-MM-DD" in result.question.reply_hint


def test_equivalent_date_coverage_does_not_displace_a_distinguishing_field():
    rent = replace(SERVICE, required_circumstances=(("housing_basis", "rental"),))
    before = replace(rent, effective_period=EffectivePeriod("filing_date", effective_until=date(2026, 3, 31)))
    after = replace(
        rent, assignment_id="rental-after",
        effective_period=EffectivePeriod("filing_date", effective_from=date(2026, 4, 1)),
    )
    ownership = replace(CONFLICT, required_circumstances=(("housing_basis", "owner"),))
    result = choose(case_locations={}, assignments=(before, after, ownership))
    assert isinstance(result, RequestClarification)
    assert result.question.missing_fields == ["housing_basis"]


def test_single_question_prefers_a_field_that_can_complete_a_possible_assignment():
    rental = replace(SERVICE, required_circumstances=(("housing_basis", "rental"),))
    competing = replace(
        CONFLICT, case_location_role="activity_location",
        effective_period=EffectivePeriod("filing_date", effective_from=date(2026, 4, 1)),
    )
    result = choose(assignments=(rental, competing))
    assert isinstance(result, RequestClarification)
    assert result.question.missing_fields == ["housing_basis"]


def test_joint_requirements_are_not_grouped_across_separate_goals():
    state = STATE.model_copy(update={
        "intent": "plan_multiple_tasks", "procedure_candidates": ["procedure-a", "procedure-b"],
    })
    main = replace(SERVICE, effective_period=EffectivePeriod("filing_date", effective_from=date(2026, 4, 1)))
    other = replace(OTHER_PROCEDURE, case_location_role="activity_location")
    result = choose(state, case_locations={}, assignments=(main, other))
    assert isinstance(result, RequestClarification)
    assert result.question.missing_fields == ["activity_location"]


def test_an_unchangeable_authority_conflict_does_not_prompt_for_another_assignment():
    pending = area(assignment_id="unresolved-office", authority_id="authority-c", role="activity_location")
    result = choose(assignments=(SERVICE, CONFLICT, pending))
    assert isinstance(result, AnswerResult)
    assert result.verification_status == "conflicting_evidence"
    assert result.missing_information == []
    assert result.official_channel is None


def test_official_assistance_is_independent_of_authority_conflict():
    result = choose(assignments=(SERVICE, CONFLICT), assistance_contacts=(CONTACT,))
    assert isinstance(result, AnswerResult)
    assert result.verification_status == "conflicting_evidence"
    assert all(INPUTS["reviewed_labels"][item] in result.explanation for item in ("authority-a", "authority-b"))
    assert result.citations == [CONTACT.citation]
    [claim] = result.claims
    assert claim.kind == "channel"
    assert claim.evidence_ids == [CONTACT.citation.passage_id]
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
    assert result.claims == []


@pytest.mark.parametrize("all_fields", [False, True])
def test_worker_persists_question_and_does_not_repeat_it_or_treat_reply_as_confirmed(queued_run, all_fields):
    factory, context, _, _ = queued_run
    assert run_worker_step(factory, **context, execute=lambda *_: STATE).status == "running"
    assignments = INPUTS["assignments"]
    expected = ["destination"]
    if all_fields:
        assignments = (replace(SERVICE, required_circumstances=(("housing_basis", "rental"),)),)
        expected.append("housing_basis")
    step = partial(choose_candidate_step, **(INPUTS | {"case_locations": {}, "assignments": assignments}))

    paused = run_worker_step(factory, **context, execute=step)
    assert paused.status == "waiting_for_information"
    with factory.begin() as db:
        [event] = read_run_events(db, **context, after_seq=paused.last_event_seq - 1).events
        question = event.question
        assert question.missing_fields == expected
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
    assert finished.result.missing_information == expected
    assert finished.result.official_channel is None


@pytest.mark.parametrize(("disposition", "note"), [
    ("unknown", "non sei sicuro o sicura"),
    ("skip", "dettagli che hai saltato"),
])
def test_deferred_fields_remain_open_and_verified_assistance_is_preserved(
    queued_run, approved_citation, disposition, note,
):
    factory, context, _, _ = queued_run
    citation, _ = approved_citation
    state = STATE.model_copy(update={"procedure_candidates": [citation.procedure_id]})
    assert run_worker_step(factory, **context, execute=lambda *_: state).status == "running"
    dated = replace(
        SERVICE, procedure_id=citation.procedure_id, unit_ids=(citation.location_id,),
        effective_period=EffectivePeriod("filing_date", effective_from=date(2026, 4, 1)),
        required_circumstances=(("housing_basis", "rental"),),
    )
    contact = AssistanceContact(
        scope=replace(
            CONTACT.scope, procedure_id=citation.procedure_id, unit_ids=(citation.location_id,),
            evidence_ref=citation.passage_id,
        ),
        citation=citation,
    )
    locations = {"destination": CaseLocation(municipality_id=citation.location_id, confirmed=True)}
    step = partial(choose_candidate_step, **(INPUTS | {
        "case_locations": locations, "assignments": (dated,), "assistance_contacts": (contact,),
        "trusted_passage_ids": TRUSTED | {citation.passage_id},
    }))
    paused = run_worker_step(factory, **context, execute=step)
    with factory.begin() as db:
        [event] = read_run_events(db, **context, after_seq=paused.last_event_seq - 1).events
        assert event.question.missing_fields == ["filing_date", "housing_basis"]
        submit_clarification_reply(
            db, **context, question_id=event.question.question_id,
            reply=ClarificationReply(
                client_reply_id=uuid4(), expected_run_revision=paused.run_revision, disposition=disposition,
            ),
        )
    review = ReviewedClaimSupport(
        kind="channel", language="it",
        statement="La fonte citata fornisce un contatto ufficiale per questa pratica.",
        official_channel=OfficialChannel(label=citation.publisher, url=citation.official_url),
        passages=(ClaimPassageSupport(citation.passage_id, contact.scope.assignment_id, CONTACT_QUOTE),),
    )
    scope = AnswerEvidenceScope(citation.procedure_id, locations, {}, {}, (contact.scope,), (review,))
    result = run_worker_step(factory, **context, execute=step, read_evidence_scope=lambda *_: scope).result
    assert note in result.explanation
    assert result.verification_status == "insufficient_evidence"
    assert result.missing_information == ["filing_date", "housing_basis"]
    assert result.official_channel.url == citation.official_url
    assert result.citations == [citation]
    assert result.claims[0].evidence_ids == [citation.passage_id]



def test_worker_resumes_applicability_after_persisted_date_and_housing_reply(queued_run):
    factory, context, _, _ = queued_run
    assert run_worker_step(factory, **context, execute=lambda *_: STATE).status == "running"

    dated = replace(
        SERVICE,
        effective_period=EffectivePeriod("filing_date", effective_from=date(2026, 4, 1)),
        required_circumstances=(("housing_basis", "owner"),),
    )
    step = partial(choose_candidate_step, **(INPUTS | {"assignments": (dated,)}))
    paused = run_worker_step(factory, **context, execute=step)
    assert paused.status == "waiting_for_information"

    with factory.begin() as db:
        [event] = read_run_events(db, **context, after_seq=paused.last_event_seq - 1).events
        assert event.question.missing_fields == ["filing_date", "housing_basis"]
        answered = submit_clarification_reply(
            db, **context, question_id=event.question.question_id,
            reply=ClarificationReply(
                client_reply_id=uuid4(), expected_run_revision=paused.run_revision,
                text="filing_date: 2026-04-01\nhousing_basis: owner",
            ),
        )
        assert answered is not None

    resumed = run_worker_step(factory, **context, execute=step)
    assert resumed.status == "running"
    with factory() as db:
        checkpoint = load_checkpoint(db, **context)
    assert checkpoint is not None
    assert checkpoint.state.next_node == "find_evidence"
    assert checkpoint.state.pending_question_id is None
    assert checkpoint.state.routing_corrections.filing_date == date(2026, 4, 1)
    assert checkpoint.state.routing_corrections.housing_basis == "owner"


@pytest.mark.parametrize(("language", "location_phrase"), [
    ("en", "the municipality where the activity takes place"),
    ("it", "il comune in cui si svolge l’attività"),
])
def test_destination_does_not_satisfy_a_distinct_activity_location_role(language, location_phrase):
    assignment = replace(
        SERVICE,
        case_location_role="activity_location",
        effective_period=EffectivePeriod("filing_date", effective_from=date(2026, 4, 1)),
        required_circumstances=(("housing_basis", "owner"),),
    )
    result = choose(
        language=language,
        case_locations={"destination": DESTINATION},
        assignments=(assignment,),
    )

    assert isinstance(result, RequestClarification)
    assert set(result.question.missing_fields) == {"activity_location", "filing_date", "housing_basis"}
    assert location_phrase in result.question.text
    assert result.resume_state.next_node == "choose_next_step"


@pytest.mark.parametrize("language", ["en", "it"])
def test_confirmed_activity_location_mismatch_excludes_route_without_irrelevant_questions(language):
    assignment = replace(
        SERVICE,
        case_location_role="activity_location",
        effective_period=EffectivePeriod("filing_date", effective_from=date(2026, 4, 1)),
        required_circumstances=(("housing_basis", "owner"),),
    )
    result = choose(
        language=language,
        case_locations={
            "activity_location": CaseLocation(municipality_id="municipality-c", confirmed=True),
        },
        assignments=(assignment,),
    )

    assert isinstance(result, AnswerResult)
    assert result.verification_status == "insufficient_evidence"
    assert result.missing_information == []
    assert result.official_channel is None
    assert result.citations == []
