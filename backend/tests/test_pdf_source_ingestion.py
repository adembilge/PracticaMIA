"""Synthetic PDF fixtures prove original-byte provenance and fail-closed review.

No downloaded government PDF, production approval or real legal advice.
"""
from io import BytesIO
from hashlib import sha256

import httpx
import pytest
from reportlab.pdfgen import canvas
from sqlalchemy import select

from app.knowledge.acquisition import fetch_official_document, fetch_official_html
from app.knowledge.catalog import candidate_sources, register_candidates
from app.knowledge.model import KnowledgeSource, KnowledgeSourceVersion
from app.knowledge.pdf_extraction import MAX_PDF_BYTES, extract_pdf
from app.knowledge.review_service import approve_version
from app.knowledge.search import resolve_approved_passage, search_approved_passages
from app.knowledge.snapshot_model import KnowledgeSnapshot
from app.knowledge.snapshots import ingest_snapshot, verify_snapshot

PDF_SOURCE = "milano-residence-form-allegato-1"
SCOPE = {
    "jurisdiction": "IT-MI-MILANO",
    "procedure_id": "milan_residence_change",
    "language": "it",
}


def sample_pdf(pages=("Residenza sintetica pagina uno", "Affitto fittizio pagina due")):
    stream = BytesIO()
    writer = canvas.Canvas(stream)
    for text in pages:
        if text:
            writer.drawString(60, 720, text)
        writer.showPage()
    writer.save()
    return stream.getvalue()


def test_pdf_extracts_page_numbered_hashed_passages():
    original = sample_pdf()
    extracted = extract_pdf(original)
    assert len(extracted.passages) == 2
    assert [p.section_path for p in extracted.passages] == ["Page 1", "Page 2"]
    assert "Residenza sintetica" in extracted.normalized_text
    for passage in extracted.passages:
        assert extracted.normalized_text[
            passage.start_offset:passage.end_offset
        ] == passage.content
        assert passage.content_sha256 == sha256(passage.content.encode()).hexdigest()


@pytest.mark.parametrize("invalid", [
    b"", b"Not a PDF", b"%PDF- garbage", b"%PDF-" + b"?" * MAX_PDF_BYTES,
])
def test_pdf_rejects_corrupted_or_oversized_originals(invalid):
    with pytest.raises(ValueError):
        extract_pdf(invalid)


def test_pdf_rejects_scanned_or_textless_pages():
    with pytest.raises(ValueError, match="no extractable text"):
        extract_pdf(sample_pdf(pages=("",)))


def test_official_fetch_accepts_pdf_without_redirect_or_html_confusion():
    url = next(item["official_url"] for item in candidate_sources()
               if item["id"] == PDF_SOURCE)
    original = sample_pdf()
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, headers={"content-type": "application/pdf"}, content=original,
        )
    )
    body, media = fetch_official_document(url, transport=transport)
    assert body == original
    assert media == "application/pdf"
    with pytest.raises(ValueError):
        fetch_official_html(url, transport=transport)


def test_pdf_403_stays_blocked_not_reconstructed():
    url = next(item["official_url"] for item in candidate_sources()
               if item["id"] == PDF_SOURCE)
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            403, headers={"content-type": "application/pdf"}, content=b"forbidden",
        )
    )
    with pytest.raises(ValueError, match="HTTP 403"):
        fetch_official_document(url, transport=transport)


def test_pdf_stored_originally_then_reviewed_cited_and_tamper_rejected(client):
    pdf = sample_pdf()
    factory = client.app.state.session_factory
    with factory.begin() as db:
        register_candidates(db)
        source = db.get(KnowledgeSource, PDF_SOURCE)
        ingested = ingest_snapshot(db, source, pdf, media_type="application/pdf")
        assert ingested.status == "pending_review"

    with factory() as db:
        version = db.get(KnowledgeSourceVersion, ingested.version_id)
        assert verify_snapshot(db, version)
        snapshot = db.get(KnowledgeSnapshot, ingested.version_id)
        assert snapshot.raw_body == pdf
        assert snapshot.media_type == "application/pdf"
        assert snapshot.extraction_version == "pdf-v1"
        assert search_approved_passages(
            db, query="residenza", limit=5, **SCOPE
        ) == []

    with factory.begin() as db:
        approve_version(
            db, version_id=ingested.version_id,
            expected_digest=sha256(pdf).hexdigest(),
            actor_subject="synthetic-pdf-reviewer",
            reason="Reviewed only a generated PDF fixture in a disposable test.",
        )

    with factory() as db:
        results = search_approved_passages(
            db, query="residenza", limit=5, **SCOPE
        )
        assert results
        assert results[0].source_id == PDF_SOURCE
        assert results[0].section_path == "Page 1"
        assert resolve_approved_passage(
            db, citation_id=results[0].citation_id, **SCOPE
        ) == results[0]
        citation = results[0].citation_id

    with factory.begin() as db:
        db.get(KnowledgeSnapshot, ingested.version_id).raw_body = sample_pdf(
            pages=("Tampered fake source",)
        )

    with factory() as db:
        assert not verify_snapshot(
            db, db.get(KnowledgeSourceVersion, ingested.version_id)
        )
        assert search_approved_passages(db, query="residenza", limit=5, **SCOPE) == []
        assert resolve_approved_passage(
            db, citation_id=citation, **SCOPE
        ) is None


def test_invalid_pdf_rolls_back_any_partial_ingestion(client):
    factory = client.app.state.session_factory
    with factory.begin() as db:
        register_candidates(db)
    with pytest.raises(ValueError):
        with factory.begin() as db:
            source = db.get(KnowledgeSource, PDF_SOURCE)
            ingest_snapshot(db, source, b"%PDF-INVALID", media_type="application/pdf")
    with factory() as db:
        assert db.scalars(select(KnowledgeSourceVersion)).all() == []
