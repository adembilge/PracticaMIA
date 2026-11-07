"""Deterministic document review without trusting OCR or municipal-rule approval."""
from app.preparation.document_review import inspect_documents


def doc(doc_id="doc-1", *, status="confirmed", value="Synthetic Via 10 Milano"):
    return {
        "id": doc_id,
        "document_type": "fictional_agreement",
        "status": status,
        "extraction_status": "needs_user_confirmation",
        "candidates": [{"field_name": "property_address", "raw_value": "OCR string"}],
        "confirmed_fields": {"property_address": value},
    }


def test_empty_and_unprocessed_documents_do_not_claim_validation():
    assert inspect_documents(facts={}, documents=[]) == {
        "status": "no_documents", "document_count": 0, "conflicts": [],
        "needs_extraction": [], "needs_confirmation": [], "needs_review": [],
        "unreadable": [], "not_legal_validation": True,
    }
    unprocessed = {"id": "first", "status": "uploaded", "confirmed_fields": {},
                   "candidates": [{"field_name": "property_address",
                                   "raw_value": "Unverified OCR string"}]}
    assert inspect_documents(facts={"property_address": "Different"},
                             documents=[unprocessed])["status"] == "needs_extraction"


def test_ocr_candidate_is_never_compared_until_user_confirms():
    sample = {
        "id": "doc-1", "status": "needs_user_confirmation",
        "extraction_status": "needs_user_confirmation",
        "candidates": [{"field_name": "property_address",
                        "raw_value": "Completely different OCR"}],
        "confirmed_fields": {},
    }
    report = inspect_documents(facts={"property_address": "Synthetic Via 10"},
                               documents=[sample])
    assert report["status"] == "needs_confirmation"
    assert report["conflicts"] == []
    sample["confirmed_fields"] = {"property_address": "Synthetic Via 10"}
    report = inspect_documents(facts={"property_address": "synthetic   via 10"},
                               documents=[sample])
    assert report["status"] == "needs_review"
    assert report["conflicts"] == []


def test_confirmed_case_mismatch_is_detected_independent_of_rules():
    report = inspect_documents(
        facts={"property_address": "Synthetic Via 10 Milano"},
        documents=[doc(value="Synthetic Via 20 Milano")],
    )
    assert report["status"] == "conflict"
    assert report["conflicts"] == [{
        "kind": "case_document_mismatch", "field": "property_address",
        "document_ids": ["doc-1"],
    }]
    assert report["not_legal_validation"] is True
    assert "Synthetic Via" not in repr(report)


def test_cross_document_disagreement_is_detected_without_case_fact():
    report = inspect_documents(facts={}, documents=[
        doc("doc-1", value="Synthetic Via 10"),
        doc("doc-2", value="Synthetic Via 20"),
    ])
    assert report["status"] == "conflict"
    assert report["conflicts"] == [{
        "kind": "cross_document_mismatch", "field": "property_address",
        "document_ids": ["doc-1", "doc-2"],
    }]


def test_review_priority_and_unrecognized_states_fail_closed():
    missing = {
        "id": "pending", "status": "needs_user_confirmation",
        "extraction_status": "needs_user_confirmation",
        "confirmed_fields": {}, "candidates": [{"field_name": "property_address"}],
    }
    unreadable = {"id": "bad", "status": "unreadable", "confirmed_fields": {}}
    status = inspect_documents(facts={}, documents=[missing, unreadable])
    assert status["status"] == "unreadable"
    assert status["unreadable"] == ["bad"]
    assert status["needs_confirmation"] == ["pending"]
    unknown = inspect_documents(
        facts={}, documents=[{"id": "strange", "status": "new_state", "confirmed_fields": {}}]
    )
    assert unknown["status"] == "needs_review"
