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
    assert {"destination_province", "destination_municipality", "street_address",
            "civic_number", "postal_code",
            "rental_registration_office_municipality",
            "rental_contract_date",
            "rental_registration_number"}.issubset(mandatory_keys)
    assert proposal["release_gates"]

def test_uploaded_public_anpr_guide_fingerprint_and_section_provenance():
    """Trace field mapping to the exact uploaded edition, not the Ministry PDF."""
    field_map = load(FIELD_MAP)
    assert field_map["version"].endswith("v3_uploaded_20261107")
    records = {item["id"]: item for item in field_map["source_records"]}
    uploaded = records["anpr_uploaded_public_guide_2025"]
    assert uploaded["source_status"] == (
        "uploaded_user_copy_inspected_not_registered_or_approved"
    )
    assert uploaded["sha256"] == (
        "7ecc161913692a6d6102931c1b8cba368647a69ce664fd682785cdfd5fbadd81"
    )
    assert uploaded["pages"] == 29
    assert uploaded["pdf_creation_date"] == "2025-04-08T13:45:45Z"
    assert uploaded["url"].startswith("https://public-anpr.github.io/")
    assert records["anpr_citizen_guide_candidate"]["url"].startswith(
        "https://sc.anpr.interno.it/"
    )
    steps = {step["step"]: step for step in field_map["guide_steps"]}
    assert steps["additional_details"]["source_section"] == "1.1.4"
    assert steps["supporting_uploads"]["source_section"] == "1.1.5"
    fields = {f["key"]: f for f in field_map["candidate_input_fields"]}
    assert "street_type" not in fields and "street_name" not in fields
    assert "rental_registration_date" not in fields
    assert fields["street_address"]["section"] == "1.1.2"
    assert fields["rental_contract_date"]["section"] == "1.1.3"
    assert fields["rental_contract_date"]["source_id"] == uploaded["id"]
    assert fields["inspection_availability"]["section"] == "1.1.4"
    attachments = field_map["attached_documents"]
    assert attachments["inspected_guide_section"] == "1.1.5"
    assert attachments["inspected_guide_max_attachment_bytes"] == 1000000
    assert attachments["inspected_guide_limit_is_current"] is False
    assert attachments["mandatory_for_this_scenario_under_anpr_guide"] == []
    assert field_map["available_for_real_user_guidance"] is False
