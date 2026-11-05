"""Canonical, length-delimited digest of source acquisition metadata.

This detects post-capture metadata drift (date, title, observed URL, method)
that is NOT covered by the raw source-body digest. It does not prove a
publisher signed the browser capture or that the information is legally
current. A privileged database actor could alter both fields and digests;
authorization, audited reviews and DB access control remain necessary.
"""
from hashlib import sha256


def metadata_sha256(
    *, fetched_url: str, media_type: str, capture_method: str,
    observed_url: str | None = None,
    observed_title: str | None = None,
    observed_last_updated: str | None = None,
) -> str:
    pieces = (
        fetched_url, media_type, capture_method, observed_url,
        observed_title, observed_last_updated,
    )
    encoded = "".join(
        "-1:" if part is None else f"{len(part)}:{part}" for part in pieces
    ).encode("utf-8")
    return sha256(encoded).hexdigest()
