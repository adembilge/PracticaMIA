"""Manual one-source acquisition from a fixed official-host allowlist.

No user-facing endpoint, crawling, redirects, external proxy variables or
automatic retries. Use only when source terms and access rules permit it.
"""
from urllib.parse import urlsplit

import httpx

from app.knowledge.catalog import ALLOWED_HOSTS
from app.knowledge.html_extraction import MAX_HTML_BYTES

MEDIA_TYPES = frozenset({"text/html", "application/xhtml+xml"})


def validate_official_url(url: str) -> None:
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS
            or parts.port is not None or parts.username or parts.password
            or not parts.path.startswith("/") or parts.query or parts.fragment):
        raise ValueError("Source URL must use an approved official HTTPS host")


def _media_type(value: str) -> str:
    media = value.split(";", 1)[0].strip().lower()
    if media not in MEDIA_TYPES:
        raise ValueError("Only HTML pages are supported in this milestone")
    return media


def fetch_official_html(url: str, *, transport=None) -> tuple[bytes, str]:
    """Fetch a single registered HTML URL. Refuse every HTTP redirect."""
    validate_official_url(url)
    with httpx.Client(
        follow_redirects=False,
        timeout=httpx.Timeout(8.0, connect=4.0),
        trust_env=False,
        transport=transport,
        headers={
            "User-Agent": "PracticaMIA-Research/0.1 (manual, one URL)",
            "Accept": "text/html, application/xhtml+xml",
        },
    ) as client:
        with client.stream("GET", url) as response:
            if response.is_redirect:
                raise ValueError("Official page redirected; verify destination manually")
            if response.status_code != 200:
                raise ValueError(f"Source retrieval failed with HTTP {response.status_code}")
            if str(response.url) != url:
                raise ValueError("Fetched URL does not match registered source")
            media = _media_type(response.headers.get("content-type", ""))
            header_size = response.headers.get("content-length")
            if header_size:
                try:
                    if int(header_size) > MAX_HTML_BYTES:
                        raise ValueError("HTML response exceeds size limit")
                except ValueError as exc:
                    raise ValueError("Invalid or oversized Content-Length") from exc
            parts, length = [], 0
            for chunk in response.iter_bytes(chunk_size=16384):
                length += len(chunk)
                if length > MAX_HTML_BYTES:
                    raise ValueError("HTML response exceeds size limit")
                parts.append(chunk)
            raw = b"".join(parts)
    if not raw:
        raise ValueError("Official HTML response is empty")
    return raw, media
