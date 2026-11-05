"""Validate browser-rendered official-source evidence metadata.

A capture is text observed in a real browser on the publisher's website,
NOT original HTTP response bytes. Its provenance must remain visible
even after a human source-review decision.
"""
from datetime import datetime, timezone
from urllib.parse import urlsplit
import re

from app.knowledge.acquisition import validate_official_url
from app.knowledge.model import KnowledgeSource


def validate_browser_metadata(
    source: KnowledgeSource, *,
    observed_url: str | None,
    observed_title: str | None,
    observed_last_updated: str | None,
) -> None:
    if source.document_type == "official_document":
        raise ValueError("Browser-rendered PDF substitutes are not accepted")
    if not observed_url or not observed_title or not observed_last_updated:
        raise ValueError("Browser-rendered text needs URL, title and update date")
    validate_official_url(observed_url)
    registered = urlsplit(source.official_url)
    observed = urlsplit(observed_url)
    if observed.hostname != registered.hostname:
        raise ValueError("Browser page is not on the same municipal publisher host")
    if registered.path == "/servizi/anagrafe/cambio-di-residenza":
        if observed.path != registered.path:
            raise ValueError("Observed service page path changed")
    else:
        reg = re.match(r"^/centro-supporto/(KA-[0-9]{5})/", registered.path)
        actual = re.match(r"^/centro-supporto/(KA-[0-9]{5})/", observed.path)
        if not reg or not actual or reg.group(1) != actual.group(1):
            raise ValueError("Browser page does not match registered article code")
    if (len(observed_title) > 300 or len(observed_title.strip()) < 8
            or "<" in observed_title or ">" in observed_title):
        raise ValueError("Invalid browser page title")
    if not re.fullmatch(r"[0-9]{2}/[0-9]{2}/[0-9]{4}", observed_last_updated):
        raise ValueError("Page update date must be DD/MM/YYYY")
    try:
        last_updated = datetime.strptime(observed_last_updated, "%d/%m/%Y")
    except ValueError as exc:
        raise ValueError("Invalid page update date") from exc
    if last_updated.date() > datetime.now(timezone.utc).date():
        raise ValueError("Page update date cannot be in the future")
