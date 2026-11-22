"""Bilingual matching and applicability checks with fictional catalogue records."""

from dataclasses import replace

import pytest

from app.agent.candidate_resolution import choose_candidate_step
from app.agent.catalogue_applicability import resolve_candidate_applicability
from app.agent.checkpoints import CheckpointState
from app.agent.contract import AnswerResult
from app.agent.intent_extraction import extract_intent, identify_intent_step
from app.agent.run_requests import StoredMessage
from app.agent.worker import RequestClarification
from app.knowledge.entity_matching import match_catalogue_names
from app.knowledge.service_areas import CaseLocation
from test_agent_intent_extraction import reviewed_name
from test_service_areas import TRUSTED, area


PROCEDURE = "address-change"
DESTINATION = CaseLocation(municipality_id="springford", confirmed=True)
CATALOGUE = (
    reviewed_name(PROCEDURE, "procedure", "residence change"),
    reviewed_name(PROCEDURE, "procedure", "cambio di residenza"),
    reviewed_name("springford", "municipality", "Springford"),
    reviewed_name("springford", "municipality", "Borgofonte"),
    reviewed_name("north-registry", "authority", "North Registry"),
    reviewed_name("north-registry", "authority", "Registro Nord"),
    replace(reviewed_name("south-registry", "authority", "S.R.O."), kind="official_acronym"),
)
NORTH = area(procedure_id=PROCEDURE, authority_id="north-registry", unit_ids=("springford",))
SOUTH = area(
    assignment_id="south", procedure_id=PROCEDURE, authority_id="south-registry",
    unit_ids=("south-bank",), evidence_ref="synthetic-passage-2",
)


def checkpoint_for(message):
    return identify_intent_step(
        message, CheckpointState(next_node="identify_intent"), catalogue_names=CATALOGUE,
    )


@pytest.mark.parametrize(("language", "text", "missing_fields", "question_field"), [
    pytest.param("en", "How do I file a residence change in Springford?", [], None, id="en-full"),
    pytest.param("it", "Come presento il cambio di residenza a Borgofonte?", [], None, id="it-full"),
    pytest.param("en", "Residence change…", ["procedure_location"], "destination", id="en-fragment"),
    pytest.param("it", "Cambio di residenza…", ["procedure_location"], "destination", id="it-fragment"),
    pytest.param("en", "Residence change in Springfrd", ["procedure_location"], "destination", id="en-place-typo"),
    pytest.param("it", "Cambio di residenza a Borgofotne", ["procedure_location"], "destination", id="it-place-typo"),
    pytest.param("en", "How do I file a residnce change in Springford?", ["procedure"], "procedure",
                 id="en-procedure-typo"),
    pytest.param("it", "Come presento il cambio di residenzza a Borgofonte?", ["procedure"], "procedure",
                 id="it-procedure-typo"),
])
def test_message_gaps_and_routing_outcomes(language, text, missing_fields, question_field):
    message = StoredMessage(text, language, None)
    state = checkpoint_for(message)
    assert state.intent == "find_procedure"
    assert state.missing_fields == missing_fields
    assert state.procedure_candidates == ([] if question_field == "procedure" else [PROCEDURE])
    assert state.next_node == ("choose_next_step" if question_field else "find_evidence")

    inputs = {
        "case_locations": {} if question_field == "destination" else {"destination": DESTINATION},
        "confirmed_dates": {}, "confirmed_circumstances": {},
        "assignments": (NORTH, SOUTH), "trusted_passage_ids": TRUSTED,
    }
    applicable = resolve_candidate_applicability(state, **inputs)
    if question_field == "procedure":
        assert applicable == {}
    elif question_field == "destination":
        assert applicable[PROCEDURE].status == "needs_information"
        assert applicable[PROCEDURE].authority_ids == ()
    else:
        assert applicable[PROCEDURE].status == "supported"
        assert applicable[PROCEDURE].authority_ids == ("north-registry",)

    if question_field:
        decision = choose_candidate_step(message, state, reviewed_labels={}, **inputs)
        assert isinstance(decision, RequestClarification)
        assert decision.question.missing_fields == [question_field]


@pytest.mark.parametrize(("typo", "entity_type", "candidate_id"), [
    ("Springfrd", "municipality", "springford"),
    ("Borgofotne", "municipality", "springford"),
    ("residnce change", "procedure", PROCEDURE),
    ("cambio di residenzza", "procedure", PROCEDURE),
    ("North Regstry", "authority", "north-registry"),
    ("Registro Nrod", "authority", "north-registry"),
])
def test_standalone_catalogue_spelling_suggestions_require_confirmation(typo, entity_type, candidate_id):
    match = match_catalogue_names(typo, list(CATALOGUE), entity_type=entity_type)
    assert match.status == "needs_confirmation"
    assert match.selected_id is None
    assert [(candidate.catalogue_id, candidate.match_type) for candidate in match.candidates] == [
        (candidate_id, "spelling_suggestion"),
    ]


@pytest.mark.parametrize(("language", "template", "authority_order"), [
    ("en", "Residence change in Springford — North Registry or {}?", ("north-registry", "south-registry")),
    ("it", "Cambio di residenza a Borgofonte — {} o Registro Nord?", ("south-registry", "north-registry")),
])
@pytest.mark.parametrize("acronym", ["SRO", "S.R.O.", "S R O"])
def test_authority_name_order_and_acronym_spelling_do_not_determine_competence(
    language, template, authority_order, acronym,
):
    message = StoredMessage(template.format(acronym), language, None)
    extraction = extract_intent(message, catalogue_names=CATALOGUE)
    matches = [
        mention.match for mention in extraction.mentions
        if any(candidate.entity_type == "authority" for candidate in mention.match.candidates)
    ]
    assert [tuple(candidate.catalogue_id for candidate in match.candidates) for match in matches] == [
        (authority,) for authority in authority_order
    ]
    by_id = {match.candidates[0].catalogue_id: match for match in matches}
    assert by_id["north-registry"].selected_id == "north-registry"
    assert by_id["south-registry"].status == "needs_confirmation"
    assert by_id["south-registry"].selected_id is None

    state = checkpoint_for(message)
    assert state.intent == "find_procedure"
    assert state.procedure_candidates == [PROCEDURE]
    assert state.missing_fields == []
    inputs = {
        "confirmed_dates": {}, "confirmed_circumstances": {},
        "assignments": (NORTH, SOUTH), "trusted_passage_ids": TRUSTED,
    }
    unconfirmed = resolve_candidate_applicability(state, case_locations={}, **inputs)[PROCEDURE]
    assert unconfirmed.status == "needs_information"
    assert unconfirmed.authority_ids == ()
    confirmed = resolve_candidate_applicability(
        state, case_locations={"destination": DESTINATION}, **inputs,
    )[PROCEDURE]
    assert confirmed.status == "supported"
    assert confirmed.authority_ids == ("north-registry",)


@pytest.mark.parametrize(("trusted_passage_ids", "status", "authority_ids"), [
    (TRUSTED, "conflicting_evidence", ("north-registry", "south-registry")),
    (frozenset(), "insufficient_evidence", ()),
])
def test_named_authorities_need_applicable_current_evidence(trusted_passage_ids, status, authority_ids):
    message = StoredMessage("Cambio di residenza: SRO o Registro Nord?", "it", None)
    state = checkpoint_for(message)
    assert state.next_node == "choose_next_step"
    inputs = {
        "case_locations": {"destination": DESTINATION}, "confirmed_dates": {}, "confirmed_circumstances": {},
        "assignments": (NORTH, replace(SOUTH, unit_ids=NORTH.unit_ids)), "trusted_passage_ids": trusted_passage_ids,
    }
    assert resolve_candidate_applicability(state, **inputs)[PROCEDURE].authority_ids == authority_ids
    decision = choose_candidate_step(
        message, state, reviewed_labels={"north-registry": "Registro Nord", "south-registry": "Registro Sud"},
        **inputs,
    )
    assert isinstance(decision, AnswerResult)
    assert decision.verification_status == status
    assert decision.official_channel is None
    assert decision.next_action is None
    assert decision.citations == []
    if authority_ids:
        assert "Registro Nord" in decision.explanation and "Registro Sud" in decision.explanation

def test_ambiguous_authority_spelling_suggestion_does_not_prefer_exact_near_match():
    competing_catalogue = [
        *CATALOGUE,
        reviewed_name("north-variant", "authority", "North Regstry"),
    ]

    match = match_catalogue_names(
        "North Regstry", competing_catalogue, entity_type="authority",
    )

    assert match.status == "ambiguous"
    assert match.selected_id is None
    assert {
        (candidate.catalogue_id, candidate.match_type)
        for candidate in match.candidates
    } == {
        ("north-registry", "spelling_suggestion"),
        ("north-variant", "exact"),
    }

