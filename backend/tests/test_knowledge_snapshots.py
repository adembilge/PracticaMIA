"""Offline tests for bounded government HTML ingestion and review-safe history."""
from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select

from app.knowledge.acquisition import fetch_official_html
from app.knowledge.catalog import register_candidates, candidate_sources
from app.knowledge.html_extraction import (
    MAX_HTML_BYTES, EXTRACTION_VERSION, extract_html,
)
from app.knowledge.model import KnowledgeSource, KnowledgeSourceVersion
from app.knowledge.snapshot_model import KnowledgePassage, KnowledgeSnapshot
from app.knowledge.snapshots import ingest_snapshot, verify_snapshot

HTML = b"""<html><head><script>delete all records</script></head>
<body><nav><p>Not source content</p></nav><main>
<h1>Synthetic residence guidance</h1>
<p>First <strong>important</strong> paragraph about a synthetic workflow.</p>
<h2>Supporting information</h2>
<p>Second paragraph, for controlled extraction tests only.</p>
<ul><li>Test-only checklist item</li></ul>
</main><footer>Footer text</footer></body></html>"""
URL = candidate_sources()[0]["official_url"]


def test_html_parser_returns_exact_spans_and_discards_non_content():
    result = extract_html(HTML)
    assert result.passages
    assert "delete all records" not in result.normalized_text
    assert "Not source content" not in result.normalized_text
    assert "Footer text" not in result.normalized_text
    assert "important" in result.normalized_text
    assert any(p.section_path == "Supporting information" for p in result.passages)
    assert all(result.normalized_text[p.start_offset:p.end_offset] == p.content
               for p in result.passages)
    assert all(sha256(p.content.encode()).hexdigest() == p.content_sha256
               for p in result.passages)


@pytest.mark.parametrize("body", [b"", b"\xff\xfe", b"<html><script>x</script></html>",
                                   b"x" * (MAX_HTML_BYTES + 1)])
def test_html_extraction_fails_closed_on_invalid_input(body):
    with pytest.raises(ValueError):
        extract_html(body)


def test_long_paragraph_splits_without_missing_words():
    text = " ".join(["Synthetic"] * 400)
    extracted = extract_html(("<p>" + text + "</p>").encode())
    assert len(extracted.passages) > 1
    assert all(0 < len(p.content) <= 1200 for p in extracted.passages)
    assert sum(p.content.count("Synthetic") for p in extracted.passages) == 400


def test_fetch_official_html_accepts_only_bounded_html():
    def server(request):
        assert request.url.scheme == "https"
        assert request.url.host == "www.comune.milano.it"
        return httpx.Response(200, headers={"content-type": "text/html; charset=utf-8"},
                              content=HTML)
    body, media = fetch_official_html(URL, transport=httpx.MockTransport(server))
    assert body == HTML
    assert media == "text/html"


@pytest.mark.parametrize("status,headers,body", [
    (302, {"location": "https://example.com/redirect"}, b""),
    (500, {"content-type": "text/html"}, b"error"),
    (200, {"content-type": "application/pdf"}, b"%PDF"),
    (200, {"content-type": "text/html"}, b"x" * (MAX_HTML_BYTES + 1)),
])
def test_fetch_rejects_redirect_status_type_and_oversize(status, headers, body):
    transport = httpx.MockTransport(
        lambda request: httpx.Response(status, headers=headers, content=body)
    )
    with pytest.raises(ValueError):
        fetch_official_html(URL, transport=transport)


@pytest.mark.parametrize("url", [
    "http://www.comune.milano.it/fake",
    "https://www.comune.milano.it.evil.example/fake",
    "https://127.0.0.1/internal",
    "https://www.comune.milano.it/servizi?override=true",
])
def test_fetch_rejects_non_curated_hosts_or_bad_protocol(url):
    with pytest.raises(ValueError):
        fetch_official_html(url, transport=httpx.MockTransport(lambda request: None))


def test_snapshot_inserts_once_and_reuses_unchanged_revision(client):
    with client.app.state.session_factory.begin() as db:
        register_candidates(db)
        source = db.get(KnowledgeSource, "milano-residence-change")
        initial = ingest_snapshot(db, source, HTML)
        assert initial.status == "pending_review"
        assert initial.revision == 1
        assert not initial.previous_approval_invalidated
    with client.app.state.session_factory.begin() as db:
        source = db.get(KnowledgeSource, "milano-residence-change")
        duplicate = ingest_snapshot(db, source, HTML)
        assert duplicate.status == "unchanged"
        assert duplicate.version_id == initial.version_id
    with client.app.state.session_factory() as db:
        versions = db.scalars(select(KnowledgeSourceVersion)).all()
        assert len(versions) == 1
        version = versions[0]
        assert version.status == "pending_review"
        assert version.reviewed_by is None
        assert version.reviewed_at is None
        assert verify_snapshot(db, version)
        snapshot = db.get(KnowledgeSnapshot, version.id)
        passages = db.scalars(select(KnowledgePassage)).all()
        assert snapshot.raw_body == HTML
        assert all(snapshot.normalized_text[p.start_offset:p.end_offset] == p.content
                   for p in passages)


def test_new_content_invalidates_prior_approval_without_mutating_old_snapshot(
    client, auth_headers,
):
    with client.app.state.session_factory.begin() as db:
        register_candidates(db)
        source = db.get(KnowledgeSource, "milano-residence-change")
        old = ingest_snapshot(db, source, HTML)
    with client.app.state.session_factory.begin() as db:
        source = db.get(KnowledgeSource, "milano-residence-change")
        version = db.get(KnowledgeSourceVersion, old.version_id)
        source.status = "approved"
        source.active_version_id = old.version_id
        version.status = "approved"
        version.reviewed_by = "synthetic-reviewer"
        version.reviewed_at = datetime.now(timezone.utc)
    url = "/api/v1/knowledge/sources"
    assert len(client.get(url, headers=auth_headers()).json()["sources"]) == 1
    changed = HTML.replace(b"First", b"Updated")
    with client.app.state.session_factory.begin() as db:
        source = db.get(KnowledgeSource, "milano-residence-change")
        new = ingest_snapshot(db, source, changed)
        assert new.status == "pending_review"
        assert new.revision == 2
        assert new.previous_approval_invalidated
        assert source.status == "candidate"
        assert source.active_version_id is None
    assert client.get(url, headers=auth_headers()).json()["status"] == "insufficient_evidence"
    with client.app.state.session_factory() as db:
        assert db.get(KnowledgeSnapshot, old.version_id).raw_body == HTML
        assert db.get(KnowledgeSnapshot, new.version_id).raw_body == changed
        assert db.get(KnowledgeSourceVersion, old.version_id).status == "approved"
        assert db.get(KnowledgeSourceVersion, new.version_id).reviewed_at is None


def test_tampered_snapshot_or_passage_disqualifies_approved_source(client, auth_headers):
    with client.app.state.session_factory.begin() as db:
        register_candidates(db)
        source = db.get(KnowledgeSource, "milano-residence-change")
        created = ingest_snapshot(db, source, HTML)
        source.status = "approved"
        source.active_version_id = created.version_id
        version = db.get(KnowledgeSourceVersion, created.version_id)
        version.status = "approved"
        version.reviewed_by = "synthetic-reviewer"
        version.reviewed_at = datetime.now(timezone.utc)
    url = "/api/v1/knowledge/sources"
    assert len(client.get(url, headers=auth_headers()).json()["sources"]) == 1
    with client.app.state.session_factory.begin() as db:
        db.get(KnowledgeSnapshot, created.version_id).raw_body = b"<p>Tampered</p>"
    assert client.get(url, headers=auth_headers()).json()["sources"] == []


def test_rejected_html_does_not_write_any_partial_version(client):
    with client.app.state.session_factory.begin() as db:
        register_candidates(db)
    with pytest.raises(ValueError):
        with client.app.state.session_factory.begin() as db:
            source = db.get(KnowledgeSource, "milano-residence-change")
            ingest_snapshot(db, source, b"<script>injection</script>")
    with client.app.state.session_factory() as db:
        assert db.scalars(select(KnowledgeSourceVersion)).all() == []
