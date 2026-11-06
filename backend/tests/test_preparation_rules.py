"""Offline correctness and fail-closed tests: no real laws, IDs, or provider calls."""
from base64 import b64encode
from io import BytesIO

import pytest
from reportlab.pdfgen import canvas

from app.preparation.crypto import decrypt_blob, encrypt_blob
from app.preparation.extract import DocumentRejected, extract_document, validate_document
from app.preparation.workflow import assess_preparation
from app.rules.engine import evaluate_condition, evaluate_rules, load_catalog, InvalidCatalog


def synthetic_catalog():
    """Fictional fixture only, never an Italian administrative ruleset."""
    return {
        "version": "synthetic-fixture-1",
        "status": "active",
        "jurisdiction": "IT-MI-MILANO",
        "procedure_id": "milan_residence_change",
        "approved_by": "synthetic-reviewer",
        "approved_at": "2026-11-06T00:00:00Z",
        "complete_scenario_coverage": True,
        "rules": [
            {
                "id": "synthetic_route",
                "kind": "route", "status": "active",
                "condition": {"field": "synthetic_eligibility", "operator": "equals", "value": "yes"},
                "result": {"route": "supported_individual"},
                "evidence_refs": ["synthetic-citation-1"],
            },
            {
                "id": "synthetic_document",
                "kind": "requirement", "status": "active",
                "condition": {"all": [
                    {"field": "synthetic_eligibility", "operator": "equals", "value": "yes"},
                    {"field": "housing_arrangement", "operator": "equals", "value": "fictional_rental"},
                ]},
                "result": {
                    "description": "Synthetic example only: inspect a fictional document",
                    "required_document_types": ["fictional_agreement"],
                },
                "evidence_refs": ["synthetic-citation-2"],
            },
        ],
    }


def test_three_valued_logic_and_short_circuits():
    assert evaluate_condition({"all": [
        {"field": "a", "operator": "equals", "value": "x"},
        {"field": "b", "operator": "equals", "value": "y"},
    ]}, {"a": "x"}) == ("UNKNOWN", {"b"})
    assert evaluate_condition({"any": [
        {"field": "a", "operator": "equals", "value": "x"},
        {"field": "b", "operator": "equals", "value": "y"},
    ]}, {"a": "x"}) == ("TRUE", set())
    assert evaluate_condition({"not": {"field": "a", "operator": "equals", "value": "x"}},
                              {"a": "z"}) == ("TRUE", set())
    assert evaluate_condition({"all": [
        {"field": "a", "operator": "equals", "value": "x"},
        {"field": "b", "operator": "equals", "value": "y"},
    ]}, {"a": "z"}) == ("FALSE", set())


def test_rules_without_approval_and_unapproved_source_never_support():
    catalog = synthetic_catalog()
    assert evaluate_rules(
        {**catalog, "status": "pending_review"},
        {"synthetic_eligibility": "yes"}, lambda _: True,
    ).decision == "blocked"
    assert evaluate_rules(catalog, {"synthetic_eligibility": "yes"},
                          lambda _: False).blocking_issues == (
        "source_unapproved_revoked_or_stale",
    )
    assert evaluate_rules(
        {**catalog, "complete_scenario_coverage": False},
        {"synthetic_eligibility": "yes"}, lambda _: True,
    ).decision == "blocked"
    assert evaluate_rules(
        {**catalog, "rules": []},
        {"synthetic_eligibility": "yes"}, lambda _: True,
    ).decision == "blocked"


def test_rule_matching_unknown_unsupported_and_document_checklist():
    catalog = synthetic_catalog()
    accept = lambda _: True
    absent = evaluate_rules(catalog, {}, accept)
    assert absent.decision == "needs_information"
    assert "synthetic_eligibility" in absent.missing_fields
    unsupported = evaluate_rules(catalog, {"synthetic_eligibility": "no",
                                            "housing_arrangement": "other"}, accept)
    assert unsupported.decision == "unsupported"
    supported = evaluate_rules(catalog, {"synthetic_eligibility": "yes",
                                          "housing_arrangement": "fictional_rental"}, accept)
    assert supported.decision == "supported"
    assert supported.required_document_types == ("fictional_agreement",)
    assert supported.checklist[0]["evidence_refs"] == ["synthetic-citation-2"]


def test_ruleset_rejects_duplicate_ids_unsafe_operators_and_duplicate_json_keys():
    catalog = synthetic_catalog()
    catalog["rules"].append(catalog["rules"][0])
    assert evaluate_rules(catalog, {}, lambda _: True).blocking_issues == ("invalid_ruleset",)
    catalog = synthetic_catalog()
    catalog["rules"][0]["condition"]["operator"] = "python_eval"
    assert evaluate_rules(catalog, {}, lambda _: True).decision == "blocked"
    with pytest.raises(InvalidCatalog):
        load_catalog('{"rules":[],"rules":[]}')


def test_graph_requires_user_review_and_current_citations():
    catalog = synthetic_catalog()
    facts = {"synthetic_eligibility": "yes", "housing_arrangement": "fictional_rental",
             "property_address": "Synthetic Via 10"}
    preview = assess_preparation(
        case_id="synthetic-case", facts=facts, catalog=catalog,
        citation_is_approved=lambda _: True, documents=[],
    )
    assert preview["status"] == "needs_documents"
    assert preview["package"] is None
    assert "missing_document:fictional_agreement" in preview["blocking_issues"]

    docs = [{
        "id": "synthetic-doc", "document_type": "fictional_agreement",
        "sha256": "x" * 64, "status": "confirmed",
        "confirmed_fields": {"property_address": "Synthetic Via 10"},
    }]
    ready = assess_preparation(
        case_id="synthetic-case", facts=facts, catalog=catalog,
        citation_is_approved=lambda _: True, documents=docs,
    )
    assert ready["status"] == "reviewable"
    assert ready["package"]["review_digest"]
    assert ready["package"]["data"]["government_submission"] == "user_only_not_submitted"

    docs[0]["confirmed_fields"]["property_address"] = "Different fictional address"
    conflict = assess_preparation(
        case_id="synthetic-case", facts=facts, catalog=catalog,
        citation_is_approved=lambda _: True, documents=docs,
    )
    assert conflict["package"] is None
    assert conflict["status"] == "needs_review"

    revoked = assess_preparation(
        case_id="synthetic-case", facts=facts, catalog=catalog,
        citation_is_approved=lambda _: False, documents=docs,
    )
    assert revoked["package"] is None
    assert revoked["status"] == "blocked"


def test_authenticated_encryption_rejects_swapped_owner_and_tampered_blob():
    key = bytes(range(32))
    ciphertext = encrypt_blob(b"synthetic", key=key, case_id="one",
                              owner_subject="alice", document_id="d1")
    assert decrypt_blob(ciphertext, key=key, case_id="one",
                        owner_subject="alice", document_id="d1",
                        expected_digest=__import__("hashlib").sha256(b"synthetic").hexdigest()) == b"synthetic"
    with pytest.raises(Exception):
        decrypt_blob(ciphertext, key=key, case_id="two",
                     owner_subject="alice", document_id="d1", expected_digest="x"*64)
    with pytest.raises(Exception):
        decrypt_blob(ciphertext[:-1] + b"0", key=key, case_id="one",
                     owner_subject="alice", document_id="d1", expected_digest="x"*64)


def sample_pdf():
    buf = BytesIO()
    writer = canvas.Canvas(buf)
    writer.drawString(25, 750, "Property address: Synthetic Via 10 Milano")
    writer.save()
    return buf.getvalue()


def test_pdf_candidate_is_evidence_anchored_not_confirmed():
    extraction = extract_document(sample_pdf(), "application/pdf")
    assert extraction["status"] == "needs_user_confirmation"
    candidate = extraction["candidates"][0]
    assert candidate["field_name"] == "property_address"
    assert candidate["verification_state"] == "needs_user_confirmation"
    assert candidate["page"] == 1


def test_rejects_mismatched_signature_and_malicious_pdf_marker():
    with pytest.raises(DocumentRejected):
        validate_document(b"not a pdf", "application/pdf")
    with pytest.raises(DocumentRejected):
        validate_document(b"%PDF-1.7\n/JavaScript\n%%EOF", "application/pdf")
    with pytest.raises(DocumentRejected):
        validate_document(b"abc", "image/png")
