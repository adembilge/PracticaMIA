"""Approved-source-cited proposal remains inactive until human signoff."""
from copy import deepcopy
import json
from pathlib import Path

from app.preparation.intake import QUESTIONS
from app.rules.engine import evaluate_rules

PROPOSAL = Path(__file__).resolve().parents[2] / (
    "requirements/milan-residence-change/"
    "italian_individual_registered_rental_candidate_v3_approved_evidence.json"
)

MILANO_VERSION = "e139e910-3a89-4994-b450-b5107d8db7dd"
ANPR_VERSION = "c89b4c40-4c41-48d5-ad52-be08e9630277"


def load():
    return json.loads(PROPOSAL.read_text(encoding="utf-8"))


def complete():
    return {question["field"]: question["expected"] for question in QUESTIONS}


def test_candidate_is_not_automatically_active_despite_source_approval():
    p = load()
    assert p["status"] == "pending_review"
    assert p["approved_by"] is None
    assert p["approved_at"] is None
    assert p["complete_scenario_coverage"] is False
    assert "review_signature" not in p
    assert p["proposal_only"] is True
    assert evaluate_rules(p, complete(), lambda ref: True).decision == "blocked"


def test_new_proposal_has_real_source_version_citations():
    p = load()
    assert len(p["rules"]) == 6
    assert {r["id"] for r in p["rules"]} >= {
        "registered_rental_anpr_fields", "tenant_attachments_reference_only",
        "applicant_only_anpr_handoff",
    }
    pdf = p["evidence_source_versions"][1]
    assert pdf["id"] == "anpr-public-docs-residence-guide"
    assert pdf["version_id"] == ANPR_VERSION
    assert pdf["source_currentness_verified"] is False
    assert pdf["archive_provenance"].startswith("public-anpr.github.io")
    all_refs = [ref for r in p["rules"] for ref in r["evidence_refs"]]
    assert all(ref.startswith((MILANO_VERSION + ":", ANPR_VERSION + ":"))
               for ref in all_refs)
    assert {ANPR_VERSION + ":0015", ANPR_VERSION + ":0018"}.issubset(all_refs)


def test_only_hypothetical_reviewed_rules_can_support_defined_route():
    p = deepcopy(load())
    # For the evaluator alone: this is not a review signature or DB approval.
    rules = p["rules"]
    hypothetical = {
        "version": p["version"],
        "status": "active",
        "jurisdiction": p["jurisdiction"],
        "procedure_id": p["procedure_id"],
        "approved_by": "UNIT_TEST_ONLY",
        "approved_at": "2000-01-01T00:00:00Z",
        "complete_scenario_coverage": True,
        "rules": rules,
    }
    assert evaluate_rules(hypothetical, complete(), lambda _: True).decision == "supported"
    assert evaluate_rules(hypothetical, complete(), lambda _: False).decision == "blocked"
    for housing in ("owner", "guest", "other"):
        facts = {**complete(), "housing_basis": housing}
        assert evaluate_rules(hypothetical, facts, lambda _: True).decision == "unsupported"
    missing = complete()
    missing.pop("housing_basis")
    result = evaluate_rules(hypothetical, missing, lambda _: True)
    assert result.decision == "needs_information"
    assert "housing_basis" in result.missing_fields
    assert hypothetical["approved_by"] == "UNIT_TEST_ONLY"
