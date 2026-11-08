"""Release checks for exactly the human-approved, technically delegated signature.

The signed catalog is useful only if the isolated Preview deployment supplies
its independently pinned public verification key and the cited database
passages are still approved at request time.
"""
from copy import deepcopy
import json
from pathlib import Path

from app.rules.approval import has_valid_human_review_signature
from app.rules.engine import evaluate_rules
from app.rules.offline_sign import check_signable_catalog
from app.rules.catalog import current_catalog
from app.preparation.intake import QUESTIONS

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "backend/app/rules/catalog.json"
REVIEWED_PATH = ROOT / "requirements/milan-residence-change/reviewer_approved_signable_catalog_v1.json"
PUBLIC_PATH = ROOT / "requirements/milan-residence-change/review_public_key_v1.b64"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def facts():
    return {q["field"]: q["expected"] for q in QUESTIONS}


def test_runtime_catalog_signed_exactly_as_owner_reviewed_bundle():
    signed = load(CATALOG_PATH)
    reviewed = load(REVIEWED_PATH)
    pub = PUBLIC_PATH.read_text(encoding="utf-8").strip()
    assert len(signed["rules"]) == 6
    assert signed["review_signature"]
    assert {k: v for k, v in signed.items() if k != "review_signature"} == reviewed
    assert reviewed["approved_by"] == "google-oauth2|113439370376814005256"
    assert reviewed["complete_scenario_coverage"] is True
    assert reviewed["status"] == "active"
    assert has_valid_human_review_signature(signed, pub)
    assert not has_valid_human_review_signature(signed, "")
    check_signable_catalog(reviewed)


def test_immutable_signature_fails_if_approval_or_rule_was_changed():
    signed = load(CATALOG_PATH)
    pub = PUBLIC_PATH.read_text(encoding="utf-8").strip()
    for name, mutate in (
        ("reviewer", lambda c: c.update(approved_by="unauthorized-user")),
        ("timestamp", lambda c: c.update(approved_at="2026-11-01T00:00:00Z")),
        ("rule", lambda c: c["rules"][0]["result"].update(route="unauthorized")),
        ("coverage", lambda c: c.update(complete_scenario_coverage=False)),
    ):
        changed = deepcopy(signed)
        mutate(changed)
        assert not has_valid_human_review_signature(changed, pub), name


def test_deployed_catalog_requires_pinned_environment_public_key(monkeypatch):
    pub = PUBLIC_PATH.read_text(encoding="utf-8").strip()
    try:
        monkeypatch.delenv("PREPARATION_RULE_REVIEW_PUBLIC_KEY", raising=False)
        current_catalog.cache_clear()
        assert current_catalog()["status"] == "pending_review"
        monkeypatch.setenv("PREPARATION_RULE_REVIEW_PUBLIC_KEY", pub)
        current_catalog.cache_clear()
        assert current_catalog()["status"] == "active"
        monkeypatch.setenv("PREPARATION_RULE_REVIEW_PUBLIC_KEY", "X" * 44)
        current_catalog.cache_clear()
        assert current_catalog()["status"] == "pending_review"
    finally:
        current_catalog.cache_clear()


def test_only_approved_evidence_and_complete_narrow_facts_enable_checklist():
    signed = load(CATALOG_PATH)
    approved = {r for rule in signed["rules"] for r in rule["evidence_refs"]}
    assert len(approved) == 11
    assert all(r.startswith((
        "c89b4c40-4c41-48d5-ad52-be08e9630277:",
        "e139e910-3a89-4994-b450-b5107d8db7dd:",
    )) for r in approved)
    outcome = evaluate_rules(signed, facts(), approved.__contains__)
    assert outcome.decision == "supported"
    assert len(outcome.checklist) == 5
    assert not outcome.required_document_types
    missing = {**facts()}
    missing.pop("housing_basis")
    x = evaluate_rules(signed, missing, approved.__contains__)
    assert x.decision == "needs_information"
    assert "housing_basis" in x.missing_fields
    for unsupported in ("owner", "guest", "other"):
        x = evaluate_rules(signed, {**facts(), "housing_basis": unsupported}, approved.__contains__)
        assert x.decision == "unsupported"
        assert not x.checklist
    first = next(iter(sorted(approved)))
    revoked = approved - {first}
    x = evaluate_rules(signed, facts(), revoked.__contains__)
    assert x.decision == "blocked"
    assert x.checklist == ()
