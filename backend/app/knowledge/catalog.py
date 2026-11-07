"""Manually curated official-source CANDIDATES. No page fetch or auto approval."""
import json
import re
from importlib.resources import files
from urllib.parse import urlsplit

from sqlalchemy.orm import Session

from app.knowledge.model import KnowledgeSource

HOST_INSTITUTIONS = {
    "www.comune.milano.it": "Comune di Milano",
    "servizicrm.comune.milano.it": "Comune di Milano",
    "sc.anpr.interno.it": "Ministero dell'Interno - ANPR",
}
ALLOWED_HOSTS = frozenset(HOST_INSTITUTIONS)
FIELDS = frozenset({
    "id", "institution", "jurisdiction", "procedure_id", "language",
    "title", "official_url", "document_type",
})


def validate_candidate(record: object) -> dict[str, str]:
    if not isinstance(record, dict) or set(record) != FIELDS:
        raise ValueError("Candidate source has unexpected or missing fields")
    for key in FIELDS:
        if not isinstance(record[key], str) or not record[key].strip():
            raise ValueError(f"Invalid candidate field: {key}")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", record["id"]):
        raise ValueError("Invalid source identifier")
    if record["jurisdiction"] != "IT-MI-MILANO":
        raise ValueError("Out-of-jurisdiction source")
    if record["procedure_id"] != "milan_residence_change":
        raise ValueError("Unreviewed procedure")
    if record["language"] not in ("it", "en"):
        raise ValueError("Unsupported language")
    if record["document_type"] not in ("faq", "service_page", "official_document"):
        raise ValueError("Unknown document type")
    parts = urlsplit(record["official_url"])
    if record["institution"] != HOST_INSTITUTIONS.get(parts.hostname):
        raise ValueError("Official source publisher does not match allowlisted host")
    if (parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS
        or parts.username or parts.password or parts.port is not None
        or not parts.path.startswith("/") or parts.query or parts.fragment):
        raise ValueError("Source must use an allowlisted official HTTPS URL")
    return dict(record)


def candidate_sources() -> list[dict[str, str]]:
    text = files("app.knowledge").joinpath("candidate_sources.json").read_text(
        encoding="utf-8"
    )
    raw = json.loads(text)
    if not isinstance(raw, list) or not raw:
        raise ValueError("Official source candidate list is empty")
    validated = [validate_candidate(item) for item in raw]
    ids = [item["id"] for item in validated]
    urls = [item["official_url"] for item in validated]
    if len(ids) != len(set(ids)) or len(urls) != len(set(urls)):
        raise ValueError("Duplicate source identifiers or URLs")
    return validated


def register_candidates(session: Session) -> int:
    """Insert new metadata only. Never overwrite or approve existing records."""
    additions = 0
    for source in candidate_sources():
        if session.get(KnowledgeSource, source["id"]) is None:
            session.add(KnowledgeSource(**source, status="candidate"))
            additions += 1
    session.flush()
    return additions
