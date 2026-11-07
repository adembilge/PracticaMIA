"""First Milan route proposal regression tests: approved citations are NOT rule approval.

All positive outcomes here use a deliberately simulated approval in memory.
The actual production catalog remains pending human review and cannot activate.
"""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from app.rules.approval import has_valid_human_review_signature
from app.rules.engine import evaluate_rules
from app.preparation.workflow import assess_preparation

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "requirements/milan-residence-change/italian_individual_candidate_v1.json"
LIVE_CATALOG = ROOT / "backend/app/rules/catalog.json"
VERIFIED_PASSAGES = {
    "e139e910-3a89-4994-b450-b5107d8db7dd:0000",
    "e139e910-3a89-4994-b450-b5107d8db7dd:0003",
    "e139e910-3a89-4994-b450-b5107d8db7dd:0005",
}

COMPLETE = {
    "citizenship_class": "italian",
    "registration_context": "already_registered_in_italy",
    "destination_municipality": "milano",
    "household_scope": "individual_no_aggregation",
}


def proposed():
    return json.loads(CANDIDATE.read_text(encoding="utf-8"))


def hypothetical_approved():
    """For unit testing only; never load this object through a live endpoint."""
    c = deepcopy(proposed())
    c["status"] = "active"
    c["complete_scenario_coverage"] = True
    c["approved_by"] = "UNIT_TEST_ONLY_NOT_A_REAL_REVIEWER"
    c["approved_at"] = "2000-01-01T00:00:00Z"
    return c


def test_candidate_remains_pending_and_live_catalog_is_unapproved():
    candidate = proposed()
    live = json.loads(LIVE_CATALOG.read_text(encoding="utf-8"))
    assert candidate["status"] == "pending_review"
    assert candidate["complete_scenario_coverage"] is False
    assert candidate["approved_by"] is None
    assert live["status"] == "pending_review"
    assert live["rules"] == []
    assert not has_valid_human_review_signature(candidate, "")


def test_existing_source_citations_are_exact_and_no_fake_reference():
    candidate = proposed()
    refs = {ref for rule in candidate["rules"] for ref in rule["evidence_refs"]}
    assert refs == VERIFIED_PASSAGES
    assert all(ref.count(":") == 1 and ref.split(":")[1].isdigit() for ref in refs)


def test_unapproved_candidate_never_generates_requirements_or_package():
    result = evaluate_rules(proposed(), COMPLETE, lambda _: True)
    assert result.decision == "blocked"
    assert result.checklist == ()
    assert result.evidence_refs == ()
    package = assess_preparation(
        case_id="synthetic-only", facts=COMPLETE, catalog=proposed(),
        citation_is_approved=lambda _: True, documents=[],
    )
    assert package["package"] is None
    assert package["status"] == "blocked"


def test_positive_branch_only_with_hypothetical_approval():
    result = evaluate_rules(
        hypothetical_approved(), COMPLETE,
        lambda citation: citation in VERIFIED_PASSAGES,
    )
    assert result.decision == "supported"
    assert set(result.applicable_rule_ids) == {
        "italian_individual_route",
        "italian_change_anpr_guidance",
        "italian_change_tari_followup",
    }
    assert len(result.checklist) == 2
    assert set(result.evidence_refs) == VERIFIED_PASSAGES - {
        "e139e910-3a89-4994-b450-b5107d8db7dd:0003"
    } | {"e139e910-3a89-4994-b450-b5107d8db7dd:0003"}
    assert not result.required_document_types


@pytest.mark.parametrize("removed_field", list(COMPLETE))
def test_missing_information_never_guesses_a_route(removed_field):
    facts = dict(COMPLETE)
    del facts[removed_field]
    result = evaluate_rules(hypothetical_approved(), facts, lambda _: True)
    assert result.decision == "needs_information"
    assert removed_field in result.missing_fields


@pytest.mark.parametrize("field,incorrect", [
    ("citizenship_class", "non_eu"),
    ("registration_context", "arrival_from_abroad"),
    ("destination_municipality", "rome"),
    ("household_scope", "joining_existing_household"),
    ("household_scope", "minors_or_multiple_adults"),
])
def test_excluded_scenarios_never_get_a_supported_route(field, incorrect):
    facts = {**COMPLETE, field: incorrect}
    result = evaluate_rules(hypothetical_approved(), facts, lambda _: True)
    assert result.decision == "unsupported"
    assert result.checklist == ()


@pytest.mark.parametrize("revoked_ref", sorted(VERIFIED_PASSAGES))
def test_source_revocation_blocks_even_complete_facts(revoked_ref):
    available = VERIFIED_PASSAGES - {revoked_ref}
    result = evaluate_rules(
        hypothetical_approved(), COMPLETE,
        lambda citation: citation in available,
    )
    assert result.decision == "blocked"
    assert result.blocking_issues == ("source_unapproved_revoked_or_stale",)


def test_no_document_requirement_invented_from_missing_evidence():
    for rule in proposed()["rules"]:
        if rule["kind"] == "requirement":
            assert rule["result"]["required_document_types"] == []


def test_requirements_never_treat_tari_as_residence_submission():
    rules = proposed()["rules"]
    tari = next(rule for rule in rules if rule["id"] == "italian_change_tari_followup")
    assert "separate TARI" in tari["result"]["description"]


def test_unverified_proposal_cannot_be_activated_by_a_boolean_flip():
    changed = proposed()
    changed["status"] = "active"
    changed["complete_scenario_coverage"] = True
    result = evaluate_rules(changed, COMPLETE, lambda _: True)
    assert result.decision == "blocked"
    assert not has_valid_human_review_signature(changed, "")


def test_incorrect_reviewer_evidence_results_in_blocked_preparation():
    result = assess_preparation(
        case_id="synthetic-only", facts=COMPLETE,
        catalog=hypothetical_approved(),
        citation_is_approved=lambda _: False, documents=[],
    )
    assert result["status"] == "blocked"
    assert result["package"] is None
