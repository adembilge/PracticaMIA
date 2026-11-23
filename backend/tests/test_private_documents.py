"""Private-document vault: default-off, consent, scanning, encryption and expiry.

Entirely synthetic fixtures. These tests do not authorize real-identity uploads.
"""
import base64
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from io import BytesIO

import pytest
from cryptography.exceptions import InvalidTag
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas
from sqlalchemy import select

from app.config import Settings
from app.knowledge import model as knowledge_model  # noqa: F401 — metadata registry
from app.database import Base
from app.main import create_app
from app.private_documents import router as document_router
from app.private_documents.model import PrivateCaseDocument
from app.private_documents.security import (
    CONSENT_VERSION, ScanUnavailable, expiry_from,
    open_bytes, scan_bytes, seal_bytes, validate_release_settings,
)
from conftest import ISSUER, AUDIENCE, JWKS_URL


def fixture_pdf():
    buf = BytesIO()
    pdf = canvas.Canvas(buf)
    pdf.drawString(24, 750, "Synthetic sample only - never a real identity document")
    pdf.save()
    return buf.getvalue()


PDF_BYTES = fixture_pdf()

def enabled_settings(database_url="sqlite+pysqlite:///:memory:"):
    return Settings(
        database_url=database_url,
        enable_task_api=True,
        enable_private_document_api=True,
        deployment_environment="production",
        private_document_key=base64.b64encode(bytes(range(32))).decode(),
        private_document_scan_url="https://scanner.example.test/check",
        private_document_scan_host="scanner.example.test",
        private_document_scan_token="s" * 40,
        private_document_cron_secret="c" * 40,
        private_document_privacy_approved=True,
        private_document_controller="Example controller for testing",
        private_document_contact="privacy@example.test",
        auth_issuer=ISSUER, auth_audience=AUDIENCE, auth_jwks_url=JWKS_URL,
    )


@pytest.fixture
def document_client(tmp_path, monkeypatch):
    settings = enabled_settings(f"sqlite+pysqlite:///{tmp_path / 'vault.sqlite3'}")
    app = create_app(settings)
    Base.metadata.create_all(app.state.engine)
    monkeypatch.setattr(document_router, "scan_bytes", lambda raw, settings: None)
    with TestClient(app) as http:
        yield http
    app.state.engine.dispose()


def upload(http, url, headers, *, consent=True):
    return http.post(
        url, headers=headers,
        data={
            "category": "housing_document",
            "privacy_ack": str(consent).lower(),
            "consent_version": CONSENT_VERSION,
        },
        files={"file": ("fictional.pdf", PDF_BYTES, "application/pdf")},
    )


def test_default_off_and_require_all_release_gates():
    disabled = create_app(Settings(enable_task_api=False))
    assert "/api/v1/conversations/tasks/{case_id}/private-documents" not in disabled.openapi()["paths"]
    with pytest.raises(ValueError, match="privacy review"):
        create_app(Settings(enable_task_api=True, enable_private_document_api=True))
    assert len(validate_release_settings(enabled_settings())) == 32
    for bad in [
        {"private_document_scan_url": "http://scanner.example.test/check"},
        {"private_document_scan_url": "https://scanner.example.test.attacker.com/check"},
        {"private_document_scan_host": "internal"},
        {"private_document_scan_token": "short"},
        {"private_document_cron_secret": ""},
        {"private_document_key": "a"},
        {"private_document_controller": ""},
        {"private_document_contact": "invalid"},
    ]:
        with pytest.raises(ValueError):
            validate_release_settings(replace(enabled_settings(), **bad))


def test_document_vault_uses_canonical_task_route_and_removes_legacy_alias(document_client, auth_headers):
    paths = document_client.app.openapi()["paths"]
    assert "/api/v1/conversations/tasks/{case_id}/private-documents" in paths
    assert "/api/v1/cases/{case_id}/private-documents" not in paths
    owner = auth_headers("alice")
    task = document_client.post("/api/v1/conversations/tasks", json={}, headers=owner)
    assert task.status_code == 201
    case_id = task.json()["id"]
    assert document_client.get(
        f"/api/v1/cases/{case_id}/private-documents", headers=owner,
    ).status_code == 404


def test_hosted_fixture_mode_only_accepts_the_isolated_preview_configuration():
    fixture = replace(
        enabled_settings("postgresql://staging.example.test/test"),
        deployment_environment="preview",
        deployment_git_branch="preview/auth-review-isolated",
        enable_preparation_api=True,
        preparation_target="isolated_staging",
        preparation_database_fingerprint="f" * 64,
        private_document_fixture_mode=True,
        private_document_privacy_approved=False,
        private_document_fixture_subject_hashes="a" * 64 + "," + "b" * 64,
        private_document_fixture_file_hashes=",".join(c * 64 for c in "cde"),
    )
    assert len(validate_release_settings(fixture)) == 32
    for changed in (
        {"deployment_environment": "production"},
        {"deployment_git_branch": "feature/untrusted"},
        {"enable_preparation_api": False},
        {"database_url": "sqlite://"},
        {"private_document_fixture_subject_hashes": "a" * 64},
        {"private_document_fixture_file_hashes": "c" * 64},
        {"private_document_fixture_mode": False},
        {"preparation_document_key": fixture.private_document_key},
    ):
        with pytest.raises(ValueError):
            validate_release_settings(replace(fixture, **changed))


def test_hosted_fixture_restrictions_apply_before_scanner(
    document_client, auth_headers, monkeypatch,
):
    app = document_client.app
    app.state.private_document_fixture_subjects = {
        sha256(value.encode()).hexdigest() for value in ("alice", "bob")
    }
    app.state.private_document_fixture_files = {sha256(PDF_BYTES).hexdigest()}
    scanned = []
    monkeypatch.setattr(document_router, "scan_bytes", lambda body, _: scanned.append(body))

    alice, bob, outsider = (auth_headers(value) for value in ("alice", "bob", "other"))
    first = document_client.post("/api/v1/conversations/tasks", json={}, headers=alice).json()["id"]
    other = document_client.post("/api/v1/conversations/tasks", json={}, headers=outsider).json()["id"]
    url = f"/api/v1/conversations/tasks/{first}/private-documents"
    other_url = f"/api/v1/conversations/tasks/{other}/private-documents"
    assert document_client.get(other_url, headers=outsider).status_code == 404
    assert upload(document_client, other_url, outsider).status_code == 404
    assert document_client.get(url, headers=bob).status_code == 404
    assert upload(document_client, url, bob).status_code == 404

    app.state.private_document_fixture_files = {"0" * 64}
    assert upload(document_client, url, alice).status_code == 422
    assert not scanned

    app.state.private_document_fixture_files = {sha256(PDF_BYTES).hexdigest()}
    result = upload(document_client, url, alice)
    assert result.status_code == 201, result.text
    assert len(scanned) == 1
    document = result.json()["id"]
    assert document_client.get(f"{url}/{document}/intelligence", headers=bob).status_code == 404
    assert document_client.delete(f"{url}/{document}", headers=bob).status_code == 404
    assert document_client.delete(f"{url}/{document}", headers=alice).status_code == 204


def test_document_upload_requires_consent_and_scanner_then_encrypts(document_client, auth_headers):
    http = document_client
    alice, bob = auth_headers("alice"), auth_headers("bob")
    case_id = http.post("/api/v1/conversations/tasks", json={}, headers=alice).json()["id"]
    url = f"/api/v1/conversations/tasks/{case_id}/private-documents"
    assert http.get(url).status_code == 401
    assert http.get(url, headers=bob).status_code == 404
    assert http.post(url, headers=alice, data={"category": "housing_document"},
                     files={"file": ("f.pdf", PDF_BYTES, "application/pdf")}).status_code == 422
    assert upload(http, url, alice, consent=False).status_code == 422
    assert upload(http, url, bob).status_code == 404

    created = upload(http, url, alice)
    assert created.status_code == 201, created.text
    out = created.json()
    assert out["review_status"] == "stored_unverified"
    assert out["official_submission"] is False
    assert out["retention_days"] == 7
    assert created.headers["cache-control"] == "private, no-store"
    assert http.get(url, headers=alice).json()[0]["id"] == out["id"]
    with http.app.state.session_factory() as db:
        doc = db.get(PrivateCaseDocument, out["id"])
        assert doc and doc.owner_subject == "alice"
        assert doc.ciphertext != PDF_BYTES
        assert doc.content_sha256 == sha256(PDF_BYTES).hexdigest()
        assert doc.consent_version == CONSENT_VERSION
        assert doc.consented_at is not None and doc.scanned_at is not None
        assert doc.expires_at - doc.uploaded_at == timedelta(days=7)
        key = http.app.state.private_document_key
        assert open_bytes(doc.ciphertext, key=key, case_id=case_id,
                          owner="alice", document_id=doc.id) == PDF_BYTES
        with pytest.raises(InvalidTag):
            open_bytes(doc.ciphertext, key=key, case_id=case_id,
                       owner="bob", document_id=doc.id)
    assert http.delete(url + "/" + out["id"], headers=bob).status_code == 404
    assert http.delete(url + "/" + out["id"], headers=alice).status_code == 204
    assert http.get(url, headers=alice).json() == []


def test_deleting_task_purges_its_private_documents(document_client, auth_headers):
    http = document_client
    alice = auth_headers("alice")
    case_id = http.post("/api/v1/conversations/tasks", json={}, headers=alice).json()["id"]
    url = f"/api/v1/conversations/tasks/{case_id}/private-documents"
    created = upload(http, url, alice)
    assert created.status_code == 201, created.text
    document_id = created.json()["id"]

    deleted = http.delete(f"/api/v1/conversations/tasks/{case_id}", headers=alice)
    assert deleted.status_code == 204
    with http.app.state.session_factory() as db:
        assert db.get(PrivateCaseDocument, document_id) is None


def test_scanner_failure_rejects_without_persisting(document_client, auth_headers, monkeypatch):
    http = document_client
    alice = auth_headers("alice")
    case_id = http.post("/api/v1/conversations/tasks", json={}, headers=alice).json()["id"]
    url = f"/api/v1/conversations/tasks/{case_id}/private-documents"
    def fail(*_args):
        raise ScanUnavailable("mocked scanner offline")
    monkeypatch.setattr(document_router, "scan_bytes", fail)
    response = upload(http, url, alice)
    assert response.status_code == 503
    assert "scanner offline" not in response.text
    assert http.get(url, headers=alice).json() == []


def test_expired_documents_are_hidden_and_purged_by_authorized_cron(document_client, auth_headers):
    http = document_client
    alice = auth_headers("alice")
    case_id = http.post("/api/v1/conversations/tasks", json={}, headers=alice).json()["id"]
    url = f"/api/v1/conversations/tasks/{case_id}/private-documents"
    doc_id = upload(http, url, alice).json()["id"]
    with http.app.state.session_factory() as db:
        row = db.get(PrivateCaseDocument, doc_id)
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    assert http.get(url, headers=alice).json() == []
    assert http.get("/internal/retention/purge").status_code == 401
    assert http.get("/internal/retention/purge", headers={"Authorization": "Bearer wrong"}).status_code == 401
    response = http.get("/internal/retention/purge",
                        headers={"Authorization": "Bearer " + "c" * 40})
    assert response.status_code == 200
    assert response.json() == {"purged": 1, "more_expired": False}
    with http.app.state.session_factory() as db:
        assert db.get(PrivateCaseDocument, doc_id) is None


def test_retention_dates_and_encryption_aad():
    now = datetime.now(timezone.utc)
    assert expiry_from(now) - now == timedelta(days=7)
    key = bytes(range(32))
    sealed = seal_bytes(b"fictional", key=key, case_id="case", owner="alice", document_id="doc")
    assert b"fictional" not in sealed
    assert open_bytes(sealed, key=key, case_id="case", owner="alice", document_id="doc") == b"fictional"
    with pytest.raises(InvalidTag):
        open_bytes(sealed, key=key, case_id="wrong", owner="alice", document_id="doc")


def test_scan_verdict_must_be_clean_and_match_digest(monkeypatch):
    from app.private_documents import security
    class FakeHTTP:
        def __init__(self, payload, status=200):
            self.payload = payload
            self.status = status
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass
        def post(self, *_, **__):
            return type("Response", (), {"status_code": self.status, "json": lambda _s: self.payload})()
    body = b"synthetic"
    digest = sha256(body).hexdigest()
    monkeypatch.setattr(security.httpx, "Client", lambda **_: FakeHTTP({"status": "clean", "sha256": digest}))
    scan_bytes(body, enabled_settings())
    monkeypatch.setattr(security.httpx, "Client", lambda **_: FakeHTTP({"status": "clean", "sha256": "bad"}))
    with pytest.raises(ScanUnavailable):
        scan_bytes(body, enabled_settings())
    monkeypatch.setattr(security.httpx, "Client", lambda **_: FakeHTTP({"status": "unknown", "sha256": digest}))
    with pytest.raises(ScanUnavailable):
        scan_bytes(body, enabled_settings())
