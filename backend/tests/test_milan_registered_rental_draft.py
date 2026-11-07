"""Single narrow registered-rental Milan route: facts are reviewed candidates, not law."""
from copy import deepcopy
import json
from pathlib import Path

from app.preparation.intake import QUESTIONS, scope_intake
from app.rules.approval import has_valid_human_review_signature
from app.rules.engine import evaluate_rules

ROOT = Path(__file__).resolve().parents[2] / "requirements" / "milan-residence-change"
CANDIDATE = ROOT / "italian_individual_registered_rental_candidate_v2.json"
FIELD_MAP = ROOT / "individual_registered_rental_anpr_field_review_v1.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def all_scope_facts():
    return {question["field"]: question["expected"] for question in QUESTIONS}


def test_fifth_question_narrows_product_scope_without_legal_eligibility():
    questions = list(QUESTIONS)
    assert len(questions) == 5
    assert questions[-1]["field"] == "housing_basis"
    assert questions[-1]["expected"] == "registered_private_rental"
    four = {question["field"]: question["expected"] for question in questions[:-1]}
    missing = scope_intake(four)
    assert missing["status"] == "needs_information"
    assert missing["next_question"]["field"] == "housing_basis"
    assert scope_intake(all_scope_facts())["status"] == "candidate_scope_complete"
    for excluded in ("owner", "guest", "other"):
        assert scope_intake({**all_scope_facts(), "housing_basis": excluded})[
            "status"] == "outside_first_candidate"


def test_proposed_v2_rules_never_activate_by_default():
    proposed = load(CANDIDATE)
    assert proposed["status"] == "pending_review"
    assert proposed["complete_scenario_coverage"] is False
    assert proposed["approved_by"] is None
    assert proposed["approved_at"] is None
    assert "review_signature" not in proposed
    assert not has_valid_human_review_signature(proposed, "")
    assert evaluate_rules(proposed, all_scope_facts(),
                          lambda ref: True).decision == "blocked"
    assert all(rule["condition"]["all"][-1] == {
        "field": "housing_basis", "operator": "equals",
        "value": "registered_private_rental",
    } for rule in proposed["rules"])


def test_hypothetical_branch_excludes_non_renters_and_unknowns():
    proposed = deepcopy(load(CANDIDATE))
    proposed["status"] = "active"
    proposed["complete_scenario_coverage"] = True
    proposed["approved_by"] = "UNIT_TEST_ONLY"
    proposed["approved_at"] = "2000-01-01T00:00:00Z"
    assert evaluate_rules(proposed, all_scope_facts(),
                          lambda ref: True).decision == "supported"
    for value in ("owner", "guest", "other"):
        facts = {**all_scope_facts(), "housing_basis": value}
        assert evaluate_rules(proposed, facts, lambda ref: True).decision == "unsupported"
    facts = all_scope_facts()
    facts.pop("housing_basis")
    missing = evaluate_rules(proposed, facts, lambda ref: True)
    assert missing.decision == "needs_information"
    assert "housing_basis" in missing.missing_fields
    assert not has_valid_human_review_signature(proposed, "")


def test_field_map_classifies_guide_sources_and_never_invents_uploads():
    proposal = load(FIELD_MAP)
    assert proposal["status"] == "pending_review"
    assert proposal["available_for_real_user_guidance"] is False
    assert proposal["authoritative_rule_catalog"] == "pending_review"
    assert proposal["supported_route_boundary"] == all_scope_facts()
    sources = {source["id"]: source for source in proposal["source_records"]}
    assert sources["anpr_citizen_guide_candidate"]["source_status"] == (
        "not_approved_in_project_registry")
    assert sources["milano_italian_residence_reviewed_passage"][
        "source_status"] == "existing_approved_excerpts"
    assert proposal["attached_documents"]["mandatory_for_this_scenario_under_anpr_guide"] == []
    assert proposal["attached_documents"]["needs_human_review"] is True
    assert proposal["legal_and_handoff_separation"]["submitted_by_practicamia"] is False
    assert proposal["legal_and_handoff_separation"]["tari_is_separate"] is True
    assert all(field["review_status"] == "pending_independent_source_review"
               for field in proposal["candidate_input_fields"])
    mandatory_keys = {field["key"] for field in proposal["candidate_input_fields"]
                      if field["importance"] == "guide_required"}
    assert {"destination_province", "destination_municipality", "street_type",
            "street_name", "civic_number", "postal_code",
            "rental_registration_office_municipality",
            "rental_registration_date",
            "rental_registration_number"}.issubset(mandatory_keys)
    assert proposal["release_gates"]
