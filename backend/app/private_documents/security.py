"""Production vault security: opt-in release gate, encrypted bytes, and fail-closed scan.

No document body, extracted text, filename, or user metadata is sent to an LLM.
The scanner sees only the file bytes and a checksum; its operator needs a DPA.
"""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import ipaddress
import re
from io import BytesIO
from urllib.parse import urlsplit

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import httpx
from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader

from app.preparation.extract import DocumentRejected, MAX_FILE_BYTES, validate_document

RETENTION_DAYS = 7
MAX_DOCS_PER_CASE = 5
CONSENT_VERSION = "private-documents-2026-11-v1"
DOC_CATEGORIES = frozenset({"housing_document", "identity_document", "other_supporting_document"})
MAX_PIXELS = 20_000_000


class ScanUnavailable(RuntimeError):
    pass


class MalwareDetected(ValueError):
    pass


def _scanner_url_valid(url: str, allowed_host: str) -> bool:
    try:
        p = urlsplit(url)
        host = p.hostname or ""
        if p.scheme != "https" or not p.path.startswith("/") or not host:
            return False
        if p.username or p.password or p.query or p.fragment or p.port not in (None, 443):
            return False
        if host.lower() != allowed_host.lower() or not re.fullmatch(r"[A-Za-z0-9.-]{4,255}", host):
            return False
        if host.endswith(".local") or host.endswith(".internal") or host == "localhost":
            return False
        try:
            ipaddress.ip_address(host)
            return False
        except ValueError:
            return True
    except ValueError:
        return False


def validate_release_settings(settings) -> bytes:
    """Reject incomplete configurations before mounting any private-file routes."""
    if not settings.enable_demo_case_api:
        raise ValueError("Private documents require authenticated cases")
    if not settings.private_document_privacy_approved:
        raise ValueError("Private documents require explicit operator privacy review")
    if not settings.private_document_controller.strip():
        raise ValueError("Private documents require a named data controller")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", settings.private_document_contact):
        raise ValueError("Private documents require a privacy contact address")
    if len(settings.private_document_cron_secret) < 32:
        raise ValueError("Private documents require a protected retention cron secret")
    if len(settings.private_document_scan_token) < 32:
        raise ValueError("Private documents require a private malware scanner credential")
    if not _scanner_url_valid(settings.private_document_scan_url,
                              settings.private_document_scan_host):
        raise ValueError("Private documents require an allowlisted HTTPS scanner")
    try:
        key = base64.b64decode(settings.private_document_key, validate=True)
    except Exception as exc:
        raise ValueError("Private documents require a separate base64 AES-256 key") from exc
    if len(key) != 32:
        raise ValueError("Private documents require a separate base64 AES-256 key")
    return key


def _aad(case_id: str, owner: str, document_id: str) -> bytes:
    return f"practicamia:private-document:v1:{case_id}:{owner}:{document_id}".encode()


def seal_bytes(raw: bytes, *, key: bytes, case_id: str, owner: str, document_id: str) -> bytes:
    from os import urandom
    nonce = urandom(12)
    return nonce + AESGCM(key).encrypt(nonce, raw, _aad(case_id, owner, document_id))


def open_bytes(sealed: bytes, *, key: bytes, case_id: str, owner: str, document_id: str) -> bytes:
    """Internal integrity helper for tests and controlled key rotation. Not an API."""
    return AESGCM(key).decrypt(sealed[:12], sealed[12:], _aad(case_id, owner, document_id))


def scan_bytes(raw: bytes, settings) -> None:
    """Scanner contract: HTTPS POST octet-stream -> {status:'clean',sha256:<same hex>}.

    Any network error, redirect, mismatched checksum, or ambiguous response rejects.
    """
    digest = sha256(raw).hexdigest()
    try:
        with httpx.Client(timeout=8, follow_redirects=False, trust_env=False) as http:
            response = http.post(
                settings.private_document_scan_url,
                content=raw,
                headers={
                    "Authorization": "Bearer " + settings.private_document_scan_token,
                    "Content-Type": "application/octet-stream",
                    "X-Content-SHA256": digest,
                },
            )
        if response.status_code != 200:
            raise ScanUnavailable("Document scanner did not return success")
        payload = response.json()
        if not isinstance(payload, dict) or payload.get("sha256") != digest:
            raise ScanUnavailable("Document scanner returned unverified verdict")
        if payload.get("status") == "infected":
            raise MalwareDetected("Document rejected by malware scanner")
        if payload.get("status") != "clean":
            raise ScanUnavailable("Document scanner returned ambiguous verdict")
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        if isinstance(exc, MalwareDetected):
            raise
        raise ScanUnavailable("Document scanner unavailable") from None


def validate_private_file(raw: bytes, mime: str) -> None:
    validate_document(raw, mime)
    if mime == "application/pdf":
        try:
            reader = PdfReader(BytesIO(raw), strict=True)
            if reader.is_encrypted or not 1 <= len(reader.pages) <= 15:
                raise DocumentRejected("Encrypted or oversized PDF is not accepted")
        except DocumentRejected:
            raise
        except Exception:
            raise DocumentRejected("Invalid PDF") from None
    else:
        try:
            with Image.open(BytesIO(raw)) as image:
                expected = "PNG" if mime == "image/png" else "JPEG"
                if image.format != expected or image.width * image.height > MAX_PIXELS:
                    raise DocumentRejected("Unsupported image content")
                image.verify()
        except DocumentRejected:
            raise
        except (UnidentifiedImageError, OSError, ValueError):
            raise DocumentRejected("Invalid image") from None


def expiry_from(now: datetime) -> datetime:
    return now + timedelta(days=RETENTION_DAYS)
