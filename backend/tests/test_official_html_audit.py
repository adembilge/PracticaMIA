"""Offline one-shot acquisition audit tests with raw byte provenance."""
from hashlib import sha256

import httpx
from app.knowledge.audit_web_sources import audit_sources
from app.knowledge.catalog import candidate_sources
from app.knowledge.batch_import import prepare_directory


def _subset(ids):
    return [x for x in candidate_sources() if x["id"] in ids]


def test_saves_exact_original_html_bytes_and_metadata(tmp_path):
    rows = _subset({"milano-residence-change", "milano-residence-faq"})
    original = (
        b"<html><main><h1>Example</h1><p>Residenza synthetic test content"
        b" created inside a disposable test runner.</p></main></html>"
    )
    def callback(request):
        if request.url.path.endswith("/KA-00330/"):
            return httpx.Response(403, text="blocked")
        return httpx.Response(200, headers={"content-type":"text/html"}, content=original)
    report = audit_sources(tmp_path / "output", sources=rows,
                           transport=httpx.MockTransport(callback))
    assert report["attempted"] == 2
    assert report["originals_captured"] == 1
    assert report["failures"] == 1
    assert (tmp_path / "output" / "originals" / "milano-residence-change.html").read_bytes() == original
    ok = next(row for row in report["sources"] if row["result"] == "original_captured")
    assert ok["sha256"] == sha256(original).hexdigest()
    assert ok["size_bytes"] == len(original)
    denied = next(row for row in report["sources"] if row["result"] == "unavailable")
    assert denied["reason"] == "HTTP 403"
    assert not (tmp_path / "output" / "originals" / "milano-residence-faq.html").exists()
    assert '"originals_captured": 1' in (tmp_path / "output" / "manifest.json").read_text()
    prepared = prepare_directory(tmp_path / "output" / "originals")
    assert len(prepared) == 1
    assert prepared[0].sha256 == sha256(original).hexdigest()


def test_rejects_redirect_invalid_media_and_non_original_content(tmp_path):
    rows = _subset({
        "milano-residence-change", "milano-residence-faq",
        "milano-eu-not-working",
    })
    def callback(request):
        path = request.url.path
        if path.endswith("/KA-00330/"):
            return httpx.Response(302, headers={"location":"/elsewhere"})
        if path.endswith("/KA-00491/"):
            return httpx.Response(
                200, headers={"content-type":"application/pdf"}, content=b"not html",
            )
        return httpx.Response(
            200, headers={"content-type":"text/html"},
            content=b"<html><body></body></html>",
        )
    report = audit_sources(tmp_path / "audit", sources=rows,
                           transport=httpx.MockTransport(callback))
    assert report["originals_captured"] == 0
    assert report["failures"] == 3
    reasons = {row["reason"] for row in report["sources"]}
    assert "redirect_not_followed" in reasons
    assert "unsupported_media_type" in reasons
    assert not list((tmp_path / "audit" / "originals").iterdir())


def test_full_curated_audit_targets_exactly_14_webpages(tmp_path):
    rows = [x for x in candidate_sources() if x["document_type"] != "official_document"]
    assert len(rows) == 14
    assert len(set(x["id"] for x in rows)) == 14
    assert all(x["official_url"].startswith("https://") for x in rows)
