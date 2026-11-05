"""Conservative single-URL acquisition from explicitly approved official hosts.

No crawling, proxy configuration, redirect following, retries or login bypass.
An HTTP block remains a block; only original response bytes are admissible.
"""
from urllib.parse import urlsplit

import httpx

from app.knowledge.catalog import ALLOWED_HOSTS
from app.knowledge.document_extraction import MEDIA_LIMITS

MEDIA_TYPES = frozenset({"text/html", "application/xhtml+xml"})


def validate_official_url(url: str) -> None:
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS
            or parts.port is not None or parts.username or parts.password
            or not parts.path.startswith("/") or parts.query or parts.fragment):
        raise ValueError("Source URL must use an approved official HTTPS host")


def _fetch(url: str, *, transport=None, allowed: frozenset[str]) -> tuple[bytes, str]:
    validate_official_url(url)
    with httpx.Client(
        follow_redirects=False,
        timeout=httpx.Timeout(8.0, connect=4.0),
        trust_env=False,
        transport=transport,
        headers={
            "User-Agent": "PracticaMIA-Research/0.1 (manual, one URL)",
            "Accept": ", ".join(sorted(allowed)),
        },
    ) as client:
        with client.stream("GET", url) as response:
            if response.is_redirect:
                raise ValueError("Official page redirected; verify destination manually")
            if response.status_code != 200:
                raise ValueError(f"Source retrieval failed with HTTP {response.status_code}")
            if str(response.url) != url:
                raise ValueError("Fetched URL does not match registered source")
            media = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
            if media not in allowed:
                raise ValueError("Official source returned an unsupported media type")
            limit = MEDIA_LIMITS[media]
            header_size = response.headers.get("content-length")
            if header_size:
                try:
                    size = int(header_size)
                except ValueError as exc:
                    raise ValueError("Invalid Content-Length") from exc
                if size < 0 or size > limit:
                    raise ValueError("Official source response exceeds size limit")
            parts, length = [], 0
            for chunk in response.iter_bytes(chunk_size=16384):
                length += len(chunk)
                if length > limit:
                    raise ValueError("Official source response exceeds size limit")
                parts.append(chunk)
            raw = b"".join(parts)
    if not raw:
        raise ValueError("Official source response is empty")
    return raw, media


def fetch_official_html(url: str, *, transport=None) -> tuple[bytes, str]:
    """Backwards-compatible strict HTML-only acquisition."""
    return _fetch(url, transport=transport, allowed=MEDIA_TYPES)


def fetch_official_document(url: str, *, transport=None) -> tuple[bytes, str]:
    """Fetch only HTML or PDF, preserving original bytes; no redirect fallback."""
    return _fetch(url, transport=transport, allowed=frozenset(MEDIA_LIMITS))
