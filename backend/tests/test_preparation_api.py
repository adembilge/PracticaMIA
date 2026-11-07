"""Isolated synthetic HTTP journey: ownership, encrypted persistence, user review.

These tests do NOT assert official legal correctness or Auth0 browser E2E.
"""
import base64
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas
from sqlalchemy import select

from app.config import Settings
from app.database import Base
from app.main import create_app
from app.preparation.models import CaseDocument, CasePreparation
from app.preparation import router as preparation_router
from conftest import ISSUER, AUDIENCE, JWKS_URL
from test_preparation_rules import synthetic_catalog


def fixture_pdf():
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(25, 750, "Property address: Synthetic Via 10 Milano")
    pdf.save()
    return buffer.getvalue()


@pytest.fixture
def preparation_client(tmp_path):
    url = f"sqlite+pysqlite:///{tmp_path / 'preparation.sqlite3'}"
    settings = Settings(
        database_url=url,
        enable_demo_case_api=True,
        enable_knowledge_catalog_api=True,
        enable_preparation_api=True,
        deployment_environment="preview",
        preparation_target="isolated_staging",
        preparation_document_key=base64.b64encode(bytes(range(32))).decode(),
        auth_issuer=ISSUER, auth_audience=AUDIENCE, auth_jwks_url=JWKS_URL,
    )
    api = create_app(settings)
    Base.metadata.create_all(api.state.engine)
    with TestClient(api) as http:
        yield http
    api.state.engine.dispose()


def test_preparation_cannot_be_enabled_in_production():
    with pytest.raises(ValueError, match="production"):
        create_app(Settings(enable_preparation_api=True,
                            deployment_environment="production"))


def test_preparation_fails_closed_without_key():
    with pytest.raises(ValueError, match="256-bit"):
        create_app(Settings(
            enable_preparation_api=True, enable_demo_case_api=True,
            enable_knowledge_catalog_api=True,
            deployment_environment="preview",
            preparation_target="isolated_staging",
        ))


def test_synthetic_private_journey_and_cross_user_protections(
    preparation_client, auth_headers, monkeypatch,
):
    http = preparation_client
    alice, bob = auth_headers("alice"), auth_headers("bob")
    created = http.post("/api/v1/cases", json={}, headers=alice)
    assert created.status_code == 201, created.text
    case_id = created.json()["id"]
    base = f"/api/v1/cases/{case_id}/preparation"

    assert http.get(base).status_code == 401
    assert http.get(base, headers=bob).status_code == 404
    assert http.get(base, headers=alice).json()["workflow"]["status"] == "blocked"
    assert http.get(base + "/checklist", headers=alice).json()["checklist"] == []

    confirmed = {
        "synthetic_eligibility": "yes",
        "housing_arrangement": "fictional_rental",
        "property_address": "Synthetic Via 10 Milano",
    }
    assert http.put(base + "/facts", json={"confirmed_facts": confirmed},
                    headers=bob).status_code == 404
    saved = http.put(base + "/facts", json={"confirmed_facts": confirmed},
                     headers=alice)
    assert saved.status_code == 200, saved.text
    assert http.get(base, headers=alice).json()["confirmed_facts"] == confirmed

    # Preview-only synthetic acknowledgment; never accept user-supplied real docs.
    up = http.post(
        base + "/documents", headers=alice,
        data={"document_type": "fictional_agreement"},
        files={"file": ("fictional.pdf", fixture_pdf(), "application/pdf")},
    )
    assert up.status_code == 403
    up = http.post(
        base + "/documents",
        headers={**alice, "X-PracticaMIA-Synthetic-Only": "YES"},
        data={"document_type": "fictional_agreement"},
        files={"file": ("fictional.pdf", fixture_pdf(), "application/pdf")},
    )
    assert up.status_code == 201, up.text
    doc = up.json()
    doc_id = doc["id"]
    assert doc["status"] == "uploaded"
    assert http.get(base + "/documents", headers=bob).status_code == 404
    assert http.post(base + f"/documents/{doc_id}/extract", headers=bob).status_code == 404

    with http.app.state.session_factory() as session:
        stored = session.scalar(select(CaseDocument).where(CaseDocument.id == doc_id))
        assert stored is not None
        assert stored.ciphertext != fixture_pdf()
        assert b"Property address" not in stored.ciphertext
        prep = session.scalar(select(CasePreparation).where(CasePreparation.case_id == case_id))
        assert prep is not None
        assert b"Synthetic Via" not in prep.facts_ciphertext

    extraction = http.post(base + f"/documents/{doc_id}/extract", headers=alice)
    assert extraction.status_code == 200, extraction.text
    candidate = extraction.json()["candidates"][0]
    assert candidate["field_name"] == "property_address"
    assert extraction.json()["status"] != "confirmed"
    assert http.post(base + f"/documents/{doc_id}/review",
                     json={"confirm_document": True}, headers=alice).status_code == 409

    invalid = http.post(
        base + f"/documents/{doc_id}/confirm-fields",
        json={"field_name": "property_address", "page": 1,
              "raw_value": "invented address", "confirmed_value": "Invented"},
        headers=alice,
    )
    assert invalid.status_code == 422
    confirmed_document = http.post(
        base + f"/documents/{doc_id}/confirm-fields",
        json={"field_name": candidate["field_name"],
              "raw_value": candidate["raw_value"],
              "page": candidate["page"],
              "confirmed_value": "Synthetic Via 10 Milano"},
        headers=alice,
    )
    assert confirmed_document.status_code == 200
    reviewed = http.post(
        base + f"/documents/{doc_id}/review",
        json={"confirm_document": True}, headers=alice,
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "confirmed"

    # Until actual approved municipal sources and a ruleset exist, even fully
    # confirmed synthetic case data NEVER generates an actionable package.
    assert http.get(base + "/package", headers=alice).json()["package"] is None

    # The following injected fixtures exist only in the isolated test process.
    monkeypatch.setattr(preparation_router, "current_catalog", synthetic_catalog)
    monkeypatch.setattr(
        preparation_router, "resolve_approved_passage",
        lambda *args, **kwargs: SimpleNamespace(
            title="Synthetic evidence", official_url="https://example.test",
            reviewed_at="synthetic-review-time",
        ),
    )
    checked = http.get(base + "/checklist", headers=alice)
    assert checked.status_code == 200
    assert checked.json()["decision"] == "supported"
    assert checked.json()["checklist"][0]["rule_id"] == "synthetic_document"

    package = http.get(base + "/package", headers=alice)
    assert package.status_code == 200
    assert package.json()["status"] == "reviewable"
    digest = package.json()["package"]["review_digest"]
    assert http.post(
        base + "/package/approve",
        json={"review_digest": "a" * 64}, headers=alice,
    ).status_code == 409
    assert http.post(
        base + "/package/approve",
        json={"review_digest": digest}, headers=bob,
    ).status_code == 404
    accepted = http.post(
        base + "/package/approve",
        json={"review_digest": digest}, headers=alice,
    )
    assert accepted.status_code == 200
    assert accepted.json()["no_government_submission"] is True
    handoff = http.get(base + "/handoff", headers=alice)
    assert handoff.status_code == 200
    assert handoff.json()["government_status"] == "not_submitted"

    # Revocation, different extracted address and deletion all invalidate
    # readiness without trusting a previously accepted digest.
    monkeypatch.setattr(preparation_router, "resolve_approved_passage",
                        lambda *args, **kwargs: None)
    assert http.get(base + "/handoff", headers=alice).status_code == 409
    monkeypatch.setattr(
        preparation_router, "resolve_approved_passage",
        lambda *args, **kwargs: SimpleNamespace(
            title="Synthetic evidence", official_url="https://example.test",
            reviewed_at="synthetic-review-time",
        ),
    )
    assert http.delete(base + f"/documents/{doc_id}", headers=bob).status_code == 404
    assert http.delete(base + f"/documents/{doc_id}", headers=alice).status_code == 204
    assert http.get(base + "/handoff", headers=alice).status_code == 409
    assert http.delete(f"/api/v1/cases/{case_id}", headers=alice).status_code == 204
    with http.app.state.session_factory() as session:
        assert session.scalar(select(CasePreparation).where(
            CasePreparation.case_id == case_id,
        )) is None
        assert session.scalar(select(CaseDocument).where(
            CaseDocument.id == doc_id,
        )) is None



def test_guided_intake_is_owner_scoped_and_does_not_activate_real_rules(
    preparation_client, auth_headers,
):
    http = preparation_client
    owner, other = auth_headers("alice"), auth_headers("bob")
    created = http.post("/api/v1/cases", json={}, headers=owner)
    assert created.status_code == 201
    base = f"/api/v1/cases/{created.json()['id']}/preparation"
    first = http.get(base, headers=owner).json()
    assert first["intake"]["next_question"]["field"] == "citizenship_class"
    assert first["intake"]["is_legal_assessment"] is False
    assert http.get(base, headers=other).status_code == 404

    facts = {
        "citizenship_class": "italian",
        "registration_context": "already_registered_in_italy",
        "destination_municipality": "milano",
        "household_scope": "individual_no_aggregation",
        "property_address": "Synthetic Via 10 Milano",
    }
    assert http.put(base + "/facts", json={"confirmed_facts": facts},
                    headers=owner).status_code == 200
    complete = http.get(base, headers=owner).json()
    assert complete["intake"]["status"] == "candidate_scope_complete"
    assert complete["workflow"]["package"] is None
    assert complete["workflow"]["rules"]["decision"] != "supported"

    for bad in ("other", "unknown", "bogus"):
        changed = {**facts, "destination_municipality": bad}
        update = http.put(base + "/facts", json={"confirmed_facts": changed},
                          headers=owner)
        if bad == "bogus":
            assert update.status_code == 422
            continue
        assert update.status_code == 200
        state = http.get(base, headers=owner).json()
        assert state["intake"]["status"] == (
            "needs_information" if bad == "unknown" else "outside_first_candidate"
        )
        assert state["workflow"]["package"] is None
    assert http.put(base + "/facts", json={"confirmed_facts": facts},
                    headers=other).status_code == 404



def test_reference_passages_only_show_currently_approved_owner_scoped_evidence(
    preparation_client, auth_headers, monkeypatch,
):
    http = preparation_client
    owner, other = auth_headers("alice"), auth_headers("bob")
    case = http.post("/api/v1/cases", json={}, headers=owner)
    assert case.status_code == 201
    base = f"/api/v1/cases/{case.json()['id']}/preparation"

    assert http.get(base + "/reference-evidence", headers=other).status_code == 404
    empty = http.get(base + "/reference-evidence", headers=owner)
    assert empty.status_code == 200
    assert empty.json()["references"] == []
    assert empty.json()["status"] == "partial_or_unavailable"
    assert empty.json()["personalized_requirements"] is False

    approved_id = preparation_router.REFERENCE_PASSAGES[0]
    def approved_only(*args, **kwargs):
        if kwargs.get("citation_id") != approved_id:
            return None
        return SimpleNamespace(
            title="Approved municipal sample",
            official_url="https://example.test/municipal",
            reviewed_at="synthetic-review-time",
            content="Verified test passage, not an administrative requirement.",
        )
    monkeypatch.setattr(preparation_router, "resolve_approved_passage", approved_only)
    result = http.get(base + "/reference-evidence", headers=owner)
    assert result.status_code == 200
    data = result.json()
    assert data["status"] == "partial_or_unavailable"
    assert len(data["references"]) == 1
    assert data["references"][0]["citation_id"] == approved_id
    assert data["personalized_requirements"] is False
    assert http.get(base + "/package", headers=owner).json()["package"] is None

    monkeypatch.setattr(preparation_router, "resolve_approved_passage",
                        lambda *args, **kwargs: None)
    revoked = http.get(base + "/reference-evidence", headers=owner)
    assert revoked.json()["references"] == []



def test_preview_case_guide_is_owner_scoped_and_never_approves_a_case(
    preparation_client, auth_headers, monkeypatch,
):
    http = preparation_client
    owner, other = auth_headers("alice"), auth_headers("bob")
    case = http.post("/api/v1/cases", json={}, headers=owner)
    assert case.status_code == 201
    base = f"/api/v1/cases/{case.json()['id']}/preparation/guide"

    assert http.post(base, json={"question": "What comes next?"},
                     headers=other).status_code == 404
    assert http.post(base, json={"question": "x"}, headers=owner).status_code == 422
    assert http.post(base, json={"question": "anything", "approve": True},
                     headers=owner).status_code == 422

    first = http.post(base, json={"question": "What comes next?",
                                  "language": "en"}, headers=owner)
    assert first.status_code == 200, first.text
    data = first.json()
    assert data["mode"] == "guided_fallback"
    assert data["action"] == "intake"
    assert data["next_question"]["field"] == "citizenship_class"
    assert data["is_legal_assessment"] is False
    assert data["government_submission_status"] == "not_submitted"

    status = http.post(base, json={"question": "What is my case status?",
                                   "language": "en"}, headers=owner)
    assert status.status_code == 200
    assert status.json()["action"] == "case_status"
    assert status.json()["status"] == "blocked"

    sources = http.post(base, json={"question": "What official ANPR sources?",
                                    "language": "it"}, headers=owner)
    assert sources.status_code == 200
    assert sources.json()["action"] == "evidence"
    assert sources.json()["is_legal_assessment"] is False
    assert sources.json()["status"] == "insufficient_evidence"

    assert http.get(base.rsplit("/", 1)[0] + "/package",
                    headers=owner).json()["package"] is None


def test_pending_municipal_rules_still_report_confirmed_document_discrepancy(
    preparation_client, auth_headers,
):
    http = preparation_client
    owner = auth_headers("alice")
    created = http.post("/api/v1/cases", json={}, headers=owner)
    assert created.status_code == 201
    base = f"/api/v1/cases/{created.json()['id']}/preparation"
    assert http.put(base + "/facts", json={"confirmed_facts": {
        "property_address": "Synthetic Via 10 Milano",
    }}, headers=owner).status_code == 200
    uploaded = http.post(
        base + "/documents",
        headers={**owner, "X-PracticaMIA-Synthetic-Only": "YES"},
        data={"document_type": "fictional_agreement"},
        files={"file": ("synthetic.pdf", fixture_pdf(), "application/pdf")},
    )
    assert uploaded.status_code == 201
    doc_id = uploaded.json()["id"]
    extracted = http.post(
        base + f"/documents/{doc_id}/extract", headers=owner,
    )
    assert extracted.status_code == 200
    # A parser suggestion cannot independently establish a conflict.
    preconfirmation = http.get(base, headers=owner).json()["workflow"]
    assert preconfirmation["document_review"]["status"] == "needs_confirmation"
    assert preconfirmation["document_review"]["conflicts"] == []
    candidate = extracted.json()["candidates"][0]
    corrected = http.post(
        base + f"/documents/{doc_id}/confirm-fields",
        json={
            "field_name": candidate["field_name"],
            "raw_value": candidate["raw_value"],
            "page": candidate["page"],
            "confirmed_value": "Synthetic Via 20 Milano",
        }, headers=owner,
    )
    assert corrected.status_code == 200
    review = http.get(base, headers=owner).json()["workflow"]
    assert review["status"] == "blocked"
    assert review["package"] is None
    assert review["document_review"]["status"] == "conflict"
    assert review["document_review"]["conflicts"][0]["field"] == "property_address"
    assert review["next_action"] == "correct_documents"

    # Fix the confirmed case fact: conflict clears but unsigned legal rules
    # still block every package and government handoff.
    assert http.put(base + "/facts", json={"confirmed_facts": {
        "property_address": "Synthetic Via 20 Milano",
    }}, headers=owner).status_code == 200
    after = http.get(base, headers=owner).json()["workflow"]
    assert after["document_review"]["conflicts"] == []
    assert after["document_review"]["status"] == "needs_review"
    assert after["status"] == "blocked"
    assert after["package"] is None
    assert http.get(base + "/handoff", headers=owner).status_code == 409
