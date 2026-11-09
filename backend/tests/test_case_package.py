"""On-demand signed, owner-scoped PDF preparation dossier. Synthetic fixtures only."""
from dataclasses import replace
from datetime import datetime, timezone
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
from reportlab.pdfgen import canvas

from app.cases import checklist_service as checked
from app.config import Settings
from app.database import Base
from app.main import create_app
from app.private_documents import router as vault_router
from app.private_documents.model import PrivateCaseDocument
from test_case_checklist import create_case, confirmed_intake, FACTS
from test_private_documents import enabled_settings

ROOT = "/api/v1/cases"


def fake_evidence(citation_id):
    matches = [
        (source_id, props) for source_id, props in checked.PINNED_SOURCE_VERSIONS.items()
        if citation_id.startswith(props[0] + ":")
    ]
    assert len(matches) == 1
    source_id, (version, url, archived) = matches[0]
    return SimpleNamespace(
        citation_id=citation_id, source_id=source_id,
        source_version_id=version, official_url=url,
        institution="Reviewed test source", title="Municipal source (synthetic test)",
        reviewed_at=datetime(2026, 11, 8, tzinfo=timezone.utc),
        retrieved_at=datetime(2026, 11, 7, tzinfo=timezone.utc),
    )


@pytest.fixture
def approved(monkeypatch):
    monkeypatch.setattr(
        checked, "resolve_approved_passage",
        lambda _db, *, citation_id, **_: fake_evidence(citation_id),
    )


def pdf_text(blob):
    assert blob.startswith(b"%PDF-")
    reader = PdfReader(BytesIO(blob))
    assert 2 <= len(reader.pages) <= 6
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def test_owner_can_download_a_cited_reviewable_draft(client, auth_headers, approved):
    alice, bob = auth_headers("alice"), auth_headers("bob")
    case_id = create_case(client, alice)
    confirmed_intake(client, alice, case_id, facts={
        **FACTS, "move_in_date": "2026-11-05",
    })
    base = f"{ROOT}/{case_id}/package"
    assert client.get(base).status_code == 401
    assert client.get(base, headers=bob).status_code == 404
    assert client.get(base + "/pdf", headers=bob).status_code == 404

    response = client.get(base, headers=alice)
    assert response.status_code == 200, response.text
    manifest = response.json()
    assert manifest["status"] == "reviewable_draft"
    assert manifest["download_allowed"] is True
    assert "private_document_processing_not_enabled" in manifest["outstanding_issues"]
    assert len(manifest["confirmed_facts"]) == 6
    assert len(manifest["checklist"]) == 5
    assert manifest["documents"] == []
    assert manifest["official_submission"] is False
    assert manifest["official_acceptance"] is False
    assert manifest["document_requirements_verified"] is False
    assert manifest["eligibility_evaluated"] is False
    assert manifest["draft_only"] is True
    assert manifest["synthetic_only"] is True
    assert "owner_subject" not in str(manifest)
    assert "alice" not in str(manifest)

    download = client.get(base + "/pdf", headers=alice)
    assert download.status_code == 200, download.text[:200]
    assert download.headers["content-type"] == "application/pdf"
    assert download.headers["cache-control"] == "private, no-store"
    assert "attachment;" in download.headers["content-disposition"]
    content = pdf_text(download.content)
    assert "DRAFT - NOT SUBMITTED" in content
    assert "Case preparation draft" in content
    assert "User-confirmed example facts" in content
    assert "Reviewed source" in content
    assert "ANPR official website" in content
    assert "NOT AN OFFICIAL APPLICATION" in content
    assert "registered_private_rental" in content
    assert "2026-11-05" in content
    assert case_id not in content
    assert "alice" not in content
    assert "officially approved" not in content.lower()


def test_unconfirmed_unsupported_and_revoked_evidence_block_pdf(
    client, auth_headers, monkeypatch, approved,
):
    alice = auth_headers("alice")
    case_id = create_case(client, alice, scoped=False)
    base = f"{ROOT}/{case_id}/package"
    before = client.get(base, headers=alice).json()
    assert before["status"] == "blocked"
    assert before["checklist"] == []
    assert client.get(base + "/pdf", headers=alice).status_code == 409

    client.patch(f"{ROOT}/{case_id}/scope",
                 json={"answers": ["yes", "yes", "yes", "no", "yes"]},
                 headers=alice)
    assert client.get(base, headers=alice).json()["status"] == "blocked"
    assert client.get(base + "/pdf", headers=alice).status_code == 409

    confirmed_intake(client, alice, case_id, facts={
        **FACTS, "housing_basis": "guest",
    })
    denied = client.get(base, headers=alice).json()
    assert "checklist_outside_first_route" in denied["outstanding_issues"]
    assert denied["checklist"] == []
    assert client.get(base + "/pdf", headers=alice).status_code == 409

    confirmed_intake(client, alice, case_id, facts=FACTS)
    assert client.get(base, headers=alice).json()["download_allowed"]
    monkeypatch.setattr(
        checked, "resolve_approved_passage",
        lambda _db, *, citation_id, **_: None,
    )
    revoked = client.get(base, headers=alice).json()
    assert revoked["status"] == "blocked"
    assert revoked["checklist"] == []
    assert client.get(base + "/pdf", headers=alice).status_code == 409

    # Changing the scope erases downstream confirmed intake.
    client.patch(f"{ROOT}/{case_id}/scope",
                 json={"answers": ["no"]}, headers=alice)
    assert client.get(base + "/pdf", headers=alice).status_code == 409


@pytest.fixture
def vault_package_client(tmp_path, monkeypatch):
    url = f"sqlite+pysqlite:///{tmp_path / 'package-vault.sqlite3'}"
    settings = replace(
        enabled_settings(url),
        enable_knowledge_catalog_api=True,
    )
    api = create_app(settings)
    Base.metadata.create_all(api.state.engine)
    monkeypatch.setattr(vault_router, "scan_bytes", lambda *_: None)
    with TestClient(api) as browser:
        yield browser
    api.state.engine.dispose()


def fixture_pdf(*lines):
    buffer = BytesIO()
    doc = canvas.Canvas(buffer)
    for i, line in enumerate(lines):
        doc.drawString(40, 750 - i * 20, line)
    doc.save()
    return buffer.getvalue()


def test_uploaded_document_blocks_until_review_and_matching_facts(
    vault_package_client, auth_headers, approved,
):
    client = vault_package_client
    alice = auth_headers("alice")
    case_id = create_case(client, alice)
    confirmed_intake(client, alice, case_id, facts={
        **FACTS, "move_in_date": "2026-11-05",
    })
    base = f"{ROOT}/{case_id}/package"
    assert client.get(base, headers=alice).json()["download_allowed"]
    doc_response = client.post(
        f"{ROOT}/{case_id}/private-documents", headers=alice,
        data={"category": "housing_document", "privacy_ack": "true",
              "consent_version": "private-documents-2026-11-v1"},
        files={"file": (
            "synthetic-only.pdf",
            fixture_pdf("Housing arrangement: Registered private rental agreement",
                        "Move-in date: 2026-11-05",
                        "Property address: Confidential fake address (should never export)"),
            "application/pdf",
        )},
    )
    assert doc_response.status_code == 201, doc_response.text
    doc_id = doc_response.json()["id"]
    assert client.get(base, headers=alice).json()["status"] == "blocked"
    assert client.get(base + "/pdf", headers=alice).status_code == 409

    intel = f"{ROOT}/{case_id}/private-documents/{doc_id}/intelligence"
    extracted = client.post(intel + "/extract", headers=alice)
    assert extracted.status_code == 200, extracted.text
    candidates = extracted.json()["candidates"]
    assert len(candidates) == 2
    review = {
        "extraction_digest": extracted.json()["extraction_digest"],
        "confirm": True,
        "selections": [
            {"field_name": c["field_name"], "candidate_id": c["candidate_id"],
             "confirmed_value": "owner" if c["field_name"] == "housing_basis"
                                else c["suggested_value"]}
            for c in candidates
        ],
    }
    reviewed = client.put(intel + "/review", headers=alice, json=review)
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["status"] == "conflict"
    assert not client.get(base, headers=alice).json()["download_allowed"]
    assert client.get(base + "/pdf", headers=alice).status_code == 409

    review["selections"][0]["confirmed_value"] = "registered_private_rental"
    # Selection order is not trusted; match the field explicitly.
    for selection in review["selections"]:
        if selection["field_name"] == "housing_basis":
            selection["confirmed_value"] = "registered_private_rental"
    assert client.put(intel + "/review", headers=alice, json=review).status_code == 200
    ready = client.get(base, headers=alice).json()
    assert ready["status"] == "reviewable_draft"
    assert ready["documents"][0]["review_status"] == "user_reviewed_unverified"
    assert ready["download_allowed"] is True
    pdf = client.get(base + "/pdf", headers=alice)
    assert pdf.status_code == 200
    content = pdf_text(pdf.content)
    assert "user_reviewed_unverified" in content
    assert "Confidential fake address" not in content
    assert "Property address" not in content
    assert doc_id not in content


def test_corrupted_private_review_fails_closed(
    vault_package_client, auth_headers, approved,
):
    client = vault_package_client
    alice = auth_headers("alice")
    case_id = create_case(client, alice)
    confirmed_intake(client, alice, case_id)
    document = client.post(
        f"{ROOT}/{case_id}/private-documents", headers=alice,
        data={"category": "housing_document", "privacy_ack": "true",
              "consent_version": "private-documents-2026-11-v1"},
        files={"file": ("synthetic.pdf", fixture_pdf("Move-in date: 2026-11-05"),
                        "application/pdf")},
    )
    doc_id = document.json()["id"]
    assert client.post(
        f"{ROOT}/{case_id}/private-documents/{doc_id}/intelligence/extract",
        headers=alice,
    ).status_code == 200
    with client.app.state.session_factory() as db:
        entry = db.get(PrivateCaseDocument, doc_id)
        entry.review_ciphertext = b"corrupted" + entry.review_ciphertext
        db.commit()
    assert client.get(f"{ROOT}/{case_id}/package", headers=alice).status_code == 503
    assert client.get(f"{ROOT}/{case_id}/package/pdf", headers=alice).status_code == 503



def test_unsupported_document_is_disclosed_but_does_not_block_non_official_draft(
    vault_package_client, auth_headers, approved,
):
    client = vault_package_client
    alice = auth_headers("alice")
    case_id = create_case(client, alice)
    confirmed_intake(client, alice, case_id, facts=FACTS)
    base = f"{ROOT}/{case_id}"
    response = client.post(
        base + "/private-documents", headers=alice,
        data={"category": "identity_document", "privacy_ack": "true",
              "consent_version": "private-documents-2026-11-v1"},
        files={"file": ("fictional.pdf", fixture_pdf("Synthetic identity test"),
                        "application/pdf")},
    )
    assert response.status_code == 201, response.text
    result = client.get(base + "/package", headers=alice)
    assert result.status_code == 200
    manifest = result.json()
    assert manifest["status"] == "reviewable_draft"
    assert manifest["download_allowed"] is True
    assert manifest["document_requirements_verified"] is False
    assert manifest["documents_legally_verified"] is False
    assert "document_unsupported_category" in manifest["outstanding_issues"]
    assert manifest["documents"][0]["review_status"] == "unsupported_category"
    pdf = client.get(base + "/package/pdf", headers=alice)
    assert pdf.status_code == 200
    text = pdf_text(pdf.content)
    assert "not been automatically extracted or validated" in text
    assert "DRAFT - NOT SUBMITTED" in text
    assert "Synthetic identity test" not in text


def test_reviewed_document_missing_case_fact_blocks_pdf(
    vault_package_client, auth_headers, approved,
):
    client = vault_package_client
    alice = auth_headers("alice")
    case_id = create_case(client, alice)
    confirmed_intake(client, alice, case_id, facts=FACTS)
    base = f"{ROOT}/{case_id}"
    result = client.post(base + "/private-documents", headers=alice,
        data={"category": "housing_document", "privacy_ack": "true",
              "consent_version": "private-documents-2026-11-v1"},
        files={"file": ("housing.pdf", fixture_pdf(
            "Move-in date: 2026-11-05"), "application/pdf")})
    assert result.status_code == 201, result.text
    doc_id = result.json()["id"]
    intel_url = base + f"/private-documents/{doc_id}/intelligence"
    extracted = client.post(intel_url + "/extract", headers=alice).json()
    reviewed = client.put(intel_url + "/review", headers=alice, json={
        "extraction_digest": extracted["extraction_digest"],
        "confirm": True,
        "selections": [{
            "field_name": "move_in_date",
            "candidate_id": extracted["candidates"][0]["candidate_id"],
            "confirmed_value": "2026-11-05",
        }],
    })
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "needs_case_information"
    package = client.get(base + "/package", headers=alice).json()
    assert "document_needs_case_information" in package["outstanding_issues"]
    assert package["download_allowed"] is False
    assert client.get(base + "/package/pdf", headers=alice).status_code == 409
