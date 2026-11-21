"""Validate the Phase 4 development set against its checked-in provenance."""

import json
from pathlib import Path
import re
from urllib.parse import urlsplit

import pytest
from pydantic import TypeAdapter

from app.agent.contract import AgentIntent, ClarificationText, Identifier, PassageId
from app.rules.approval import has_valid_human_review_signature
from app.rules.engine import JURISDICTION, PROCEDURE, evaluate_rules, load_catalog


ROOT = Path(__file__).resolve().parents[2]
PLANNING = ROOT / "planning/practicamia-2"
REQUIREMENTS = ROOT / "requirements/milan-residence-change"
DATA = json.loads((ROOT / "evals/fixtures/phase04_agent_development.json").read_text(encoding="utf-8"))
REFERENCES = DATA["references"]
CASES = DATA["cases"]
CATALOG = load_catalog((ROOT / "backend/app/rules/catalog.json").read_text(encoding="utf-8"))
IDENTIFIERS = TypeAdapter(list[Identifier])
INTENTS = TypeAdapter(AgentIntent)
MESSAGES = TypeAdapter(ClarificationText)
PASSAGES = TypeAdapter(list[PassageId])
ACTIONS_BY_OUTCOME = {
    "verified_guidance": {"open_official_channel"},
    "clarification": {"provide_information", "provide_redacted_excerpt"},
    "source_gap": {"revalidate_sources", "check_current_form", "reassess_destination", "verify_filing_channel"},
    "choose_goal": {"choose_active_goal"},
    "restore_question": {"provide_information"},
    "intake_confirmation_required": {"confirm_saved_intake"},
    "intake_confirmed": {"saved_intake_confirmed"},
}
QUESTION_OUTCOMES = {"clarification", "choose_goal"}


def _check_section(reference, prefix):
    filename, _, anchor = reference.partition("#")
    assert filename.startswith(prefix) and "/" not in filename and filename.endswith(".md")
    contents = (PLANNING / filename).read_text(encoding="utf-8")
    if anchor:
        headings = re.findall(r"^#+ (.+)$", contents, flags=re.M)
        assert anchor in {re.sub(r"[^a-z0-9 -]", "", heading.lower()).replace(" ", "-") for heading in headings}
    return contents


def test_development_coverage_and_reference_provenance():
    assert DATA["schema_version"] == 1 and DATA["case_origin"] == "synthetic_from_phase2"
    assert DATA["languages"] == ["en", "it"]
    assert len({case["id"] for case in CASES}) == len(CASES)
    assert {"wrong_authority", "missing_location", "stale_source", "correction", "multiple_goals", "resumption"} <= {
        tag for case in CASES for tag in case["tags"]
    }
    assert len({ref.get("authority_id") for ref in REFERENCES.values() if ref.get("authority_id")}) >= 3
    assert len({ref["jurisdiction"] for ref in REFERENCES.values() if ref["jurisdiction"]}) >= 3

    public_key = (REQUIREMENTS / "review_public_key_v1.b64").read_text(encoding="utf-8").strip()
    assert has_valid_human_review_signature(CATALOG, public_key)
    rules = {rule["id"]: rule for rule in CATALOG["rules"]}
    review_record = json.loads((
        REQUIREMENTS / "italian_individual_registered_rental_candidate_v3_approved_evidence.json"
    ).read_text(encoding="utf-8"))
    approved_versions = {
        source["id"]: source["version_id"] for source in review_record["evidence_source_versions"]
        if source["status_at_review"] == "approved"
    }
    candidate_sources = json.loads(
        (ROOT / "backend/app/knowledge/candidate_sources.json").read_text(encoding="utf-8")
    )
    candidates = {source["id"]: source for source in candidate_sources}
    authority_labels = {}
    for reference in REFERENCES.values():
        phase3 = _check_section(reference["phase3_section"], "phase-03-")
        assert urlsplit(reference["url"]).scheme == "https" and reference["locator"].strip()
        if authority := reference.get("authority_id"):
            assert authority_labels.setdefault(authority, reference["authority_label"]) == reference["authority_label"]
        if signed := reference.get("signed_evidence"):
            assert reference["procedure_id"] == PROCEDURE and reference["jurisdiction"] == JURISDICTION
            assert signed["version_id"] == approved_versions[signed["source_id"]]
            assert reference["url"] == candidates[signed["source_id"]]["official_url"]
            passages = PASSAGES.validate_python(signed["passage_ids"])
            assert passages and all(passage.split(":")[0] == signed["version_id"] for passage in passages)
            assert set(passages) <= set(rules[signed["rule_id"]]["evidence_refs"])
        else:
            assert reference["url"] in phase3


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_eval_case_records_safe_outcomes_for_each_turn(case):
    _check_section(case["phase2_section"], "phase-02-")
    allowed_refs = set(case["reference_ids"])
    assert allowed_refs <= REFERENCES.keys()
    reference_authorities = {REFERENCES[ref].get("authority_id") for ref in allowed_refs}
    reference_procedures = {REFERENCES[ref]["procedure_id"] for ref in allowed_refs}
    opening = case["steps"][0]
    assert opening["event"] == "message"
    INTENTS.validate_python(case["opening_intent"])
    opening_procedures = IDENTIFIERS.validate_python(case["opening_procedure_ids"])
    assert len(opening_procedures) == len(set(opening_procedures))
    assert set(opening_procedures) <= reference_procedures
    if "procedure_ids" in opening["expect"]:
        assert set(opening_procedures) == set(opening["expect"]["procedure_ids"])
    if profile := case.get("initial_profile"):
        assert profile in DATA["profiles"]

    previous, pending = {}, None
    withdrawn = set()
    for step in case["steps"]:
        assert step["id"] not in previous
        event, expected = step["event"], step["expect"]
        outcome, action = expected["outcome"], expected["next_action"]
        assert action in ACTIONS_BY_OUTCOME[outcome] and expected["acceptance"].strip()
        citation_refs = set(IDENTIFIERS.validate_python(expected.get("citation_refs", [])))
        excluded_refs = set(IDENTIFIERS.validate_python(expected.get("excluded_refs", [])))
        authority_ids = set(IDENTIFIERS.validate_python(expected.get("authority_ids", [])))
        candidates = set(IDENTIFIERS.validate_python(expected.get("candidate_authority_ids", [])))
        fields = IDENTIFIERS.validate_python(expected.get("fields", []))
        procedure_ids = IDENTIFIERS.validate_python(expected.get("procedure_ids", []))
        assert citation_refs | excluded_refs <= allowed_refs and not citation_refs & excluded_refs
        assert authority_ids | candidates <= reference_authorities
        assert set(procedure_ids) <= reference_procedures
        assert not citation_refs & withdrawn

        if event in {"message", "reply"}:
            assert set(step["text"]) == set(DATA["languages"])
            assert len({MESSAGES.validate_python(text) for text in step["text"].values()}) == 2
        elif event == "confirm_intake":
            assert step.get("after_step") in previous and "facts" in step and "text" not in step
        elif event == "confirm_intake":
            assert step.get("after_step") in previous and "facts" in step and "text" not in step
        else:
            assert event in {"reopen", "source_change"} and "text" not in step
        if event == "source_change":
            revoked = step["withdrawn_ref"]
            assert revoked in allowed_refs and revoked in excluded_refs
            assert any(revoked in turn.get("citation_refs", []) for turn in previous.values())
            withdrawn.add(revoked)
        if event in {"reply", "reopen"}:
            assert step["question_step"] == pending
            asked = previous[pending]
            assert asked["outcome"] in QUESTION_OUTCOMES
            if event == "reopen":
                assert outcome == "restore_question" and fields == asked["fields"]
            else:
                if asked["outcome"] == "choose_goal":
                    chosen = step["selected_procedure_id"]
                    assert chosen in asked["procedure_ids"] and procedure_ids == [chosen]
                pending = None
        if outcome in QUESTION_OUTCOMES:
            assert fields
            pending = step["id"]
        if outcome == "choose_goal":
            assert len(set(procedure_ids)) >= 2 and fields == ["active_goal"]
        if outcome == "verified_guidance":
            assert citation_refs and authority_ids and not fields
            assert all(REFERENCES[ref].get("signed_evidence") for ref in citation_refs)
            assert authority_ids <= {REFERENCES[ref].get("authority_id") for ref in citation_refs}
        else:
            assert not citation_refs and not authority_ids
        previous[step["id"]] = expected


@pytest.mark.parametrize(
    "case", [case for case in CASES if "initial_profile" in case], ids=lambda case: case["id"],
)
def test_pinned_milan_steps_agree_with_the_signed_rule_engine(case):
    facts = DATA["profiles"][case["initial_profile"]] | case.get("initial_facts", {})
    approved = {passage for rule in CATALOG["rules"] for passage in rule["evidence_refs"]}
    for step in case["steps"]:
        facts.update(step.get("facts", {}))
        if revoked := step.get("withdrawn_ref"):
            approved.difference_update(REFERENCES[revoked]["signed_evidence"]["passage_ids"])
        expected = step["expect"]
        present_facts = {field: value for field, value in facts.items() if value is not None}
        result = evaluate_rules(CATALOG, present_facts, approved.__contains__)
        if expected["outcome"] == "verified_guidance":
            required_passages = {
                passage for ref in expected["citation_refs"]
                for passage in REFERENCES[ref]["signed_evidence"]["passage_ids"]
            }
            assert result.decision == "supported" and required_passages <= set(result.evidence_refs)
        elif expected["next_action"] == "revalidate_sources":
            assert result.decision == "blocked" and not result.evidence_refs
        elif expected["next_action"] == "reassess_destination":
            assert result.decision == "unsupported" and not result.evidence_refs
        elif expected.get("fields") == ["destination_municipality"]:
            assert result.decision == "needs_information" and result.missing_fields == ("destination_municipality",)
        elif expected["next_action"] == "check_current_form":
            assert expected["excluded_refs"] == ["anpr_applicant_handoff"]
            assert result.decision == "supported" and not expected.get("citation_refs")
