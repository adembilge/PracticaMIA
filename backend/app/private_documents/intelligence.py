"""Bounded local document intelligence for opt-in encrypted vault records.

Only annotated synthetic test fixtures are used in CI. Real-document feature
flags are OFF until malware scanning, privacy review, retention and E2E pass.

Only narrow typed labels are extracted; never persist full PDF/OCR pages.
No document text is sent to OpenRouter or any LLM, and no value becomes a
confirmed case fact merely because it appeared in a document.
"""
from __future__ import annotations

from datetime import date
from hashlib import sha256
import json
import re
from typing import Any

from app.preparation.extract import extract_document, DocumentRejected

REVIEW_VERSION = "private-document-review-v1"
MAX_CANDIDATES = 8
MAX_REVIEW_BYTES = 12000
MAX_PAGES = 15

HOUSING_RE = re.compile(
    r"(?im)^(?:housing arrangement|housing basis|housing_basis|"
    r"titolo di occupazione|titolo di alloggio)\s*:\s*(?P<value>[^\r\n]{2,100})\s*$"
)
MOVE_DATE_RE = re.compile(
    r"(?im)^(?:move-in date|move in date|move_in_date|"
    r"data (?:del )?trasferimento)\s*:\s*(?P<value>[^\r\n]{8,24})\s*$"
)
HOUSING_VALUES = {
    "registered_private_rental": "registered_private_rental",
    "registered private rental": "registered_private_rental",
    "registered private rental agreement": "registered_private_rental",
    "contratto di locazione registrato": "registered_private_rental",
    "owner": "owner",
    "proprietario": "owner",
    "proprietaria": "owner",
    "guest": "guest",
    "ospite": "guest",
    "other": "other",
    "altro": "other",
}
HOUSING_CHOICES = frozenset({
    "registered_private_rental", "owner", "guest", "other"
})
REVIEW_FIELDS = frozenset({"housing_basis", "move_in_date"})


def valid_move_date(value: str) -> bool:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        parsed = date.fromisoformat(value)
        return 1900 <= parsed.year <= 2100
    except ValueError:
        return False


def valid_confirmation(field: str, value: str) -> bool:
    if field == "housing_basis":
        return value in HOUSING_CHOICES
    if field == "move_in_date":
        return valid_move_date(value)
    return False


def _candidate(field: str, raw: str, value: str, page: int, digest: str) -> dict:
    # Only known enum/date values are allowed into metadata; no free text.
    fingerprint = f"{digest}:{field}:{page}:{raw}:{value}"
    return {
        "candidate_id": sha256(fingerprint.encode("utf-8")).hexdigest(),
        "field_name": field,
        "raw_value": raw,
        "suggested_value": value,
        "page": page,
        "verification_state": "needs_user_confirmation",
    }


def extract_intake_candidates(body: bytes, media_type: str, digest: str) -> dict:
    """No model inference: exact labels and known enum/date formats only.

    Existing PDF/OCR parser returns memory-only pages; these are discarded.
    """
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise DocumentRejected("Invalid document integrity metadata")
    if sha256(body).hexdigest() != digest:
        raise DocumentRejected("Document integrity mismatch")
    extraction = extract_document(body, media_type)
    if extraction["status"] == "unreadable":
        return {"status": "unreadable", "candidates": [], "ambiguous_fields": []}
    candidates: list[dict] = []
    seen: set[str] = set()
    field_values: dict[str, set[str]] = {}
    for page in extraction["pages"]:
        number = page["page"]
        text = page["text"]
        if type(number) is not int or not 1 <= number <= MAX_PAGES:
            raise DocumentRejected("Invalid document page metadata")
        for match in HOUSING_RE.finditer(text):
            raw = " ".join(match.group("value").split())
            normalized = HOUSING_VALUES.get(raw.casefold())
            if normalized is not None:
                c = _candidate("housing_basis", raw, normalized, number, digest)
                if c["candidate_id"] not in seen:
                    seen.add(c["candidate_id"])
                    candidates.append(c)
                    field_values.setdefault("housing_basis", set()).add(normalized)
        for match in MOVE_DATE_RE.finditer(text):
            raw = match.group("value").strip()
            if valid_move_date(raw):
                c = _candidate("move_in_date", raw, raw, number, digest)
                if c["candidate_id"] not in seen:
                    seen.add(c["candidate_id"])
                    candidates.append(c)
                    field_values.setdefault("move_in_date", set()).add(raw)
        if len(candidates) > MAX_CANDIDATES:
            raise DocumentRejected("Too many extracted field suggestions")
    if not candidates:
        return {"status": "no_supported_fields", "candidates": [], "ambiguous_fields": []}
    return {
        "status": "needs_user_confirmation",
        "candidates": candidates,
        "ambiguous_fields": sorted(field for field, values in field_values.items()
                                   if len(values) > 1),
    }


def extraction_digest(document_digest: str, result: dict) -> str:
    # Review token changes if a document or its bounded candidate list changes.
    canonical = json.dumps(
        [document_digest, result["status"], result["candidates"]],
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


def new_review(body: bytes, media_type: str, digest: str) -> dict:
    result = extract_intake_candidates(body, media_type, digest)
    result.update({
        "version": REVIEW_VERSION,
        "extraction_digest": extraction_digest(digest, result),
        "confirmed_fields": {},
        "selected_evidence": {},
        "user_reviewed": False,
    })
    return result


def validate_user_review(review: dict, *, token: str, selections: list[dict]) -> dict:
    if review.get("version") != REVIEW_VERSION or (
        review.get("status") != "needs_user_confirmation"
    ):
        raise ValueError("Extract supported fields first")
    if not isinstance(token, str) or token != review.get("extraction_digest"):
        raise ValueError("Extraction changed; reload suggestions")
    candidates = review.get("candidates", [])
    if not candidates or not isinstance(selections, list) or len(selections) > 2:
        raise ValueError("Unsupported document review")
    fields = {c["field_name"] for c in candidates}
    if not fields or len(selections) != len(fields):
        raise ValueError("Each extracted field needs one explicit review")
    options = {(c["field_name"], c["candidate_id"]) for c in candidates}
    seen: set[str] = set()
    chosen: dict[str, str] = {}
    evidence: dict[str, str] = {}
    for selection in selections:
        if not isinstance(selection, dict) or set(selection) != {
            "field_name", "candidate_id", "confirmed_value"
        }:
            raise ValueError("Unexpected field review")
        field = selection["field_name"]
        candidate_id = selection["candidate_id"]
        value = selection["confirmed_value"]
        if not isinstance(field, str) or not isinstance(candidate_id, str) or (
            not isinstance(value, str)
        ) or field in seen or (field, candidate_id) not in options or (
            not valid_confirmation(field, value)
        ):
            raise ValueError("Review does not match extracted evidence")
        seen.add(field)
        chosen[field] = value
        evidence[field] = candidate_id
    if seen != fields:
        raise ValueError("Missing field review")
    return {**review, "confirmed_fields": chosen, "selected_evidence": evidence,
            "user_reviewed": True}


def compare_review(review: dict | None, *, intake_facts: dict | None,
                   intake_confirmed: bool, document_id: str) -> dict:
    """Recompute disagreement on every owner request; never persist 'match'."""
    if review is None:
        return {
            "status": "needs_extraction", "candidates": [], "confirmed_fields": {},
            "extraction_digest": None, "comparisons": [], "ambiguous_fields": [],
            "user_reviewed": False,
        }
    status = review.get("status")
    confirmed = review.get("confirmed_fields") if review.get("user_reviewed") else {}
    confirmed = confirmed if isinstance(confirmed, dict) else {}
    results: list[dict] = []
    for field, confirmed_value in sorted(confirmed.items()):
        case_value = (intake_facts or {}).get(field) if intake_confirmed else None
        results.append({
            "field_name": field,
            "reviewed_value": confirmed_value,
            "case_value": case_value,
            "comparison": (
                "no_confirmed_case_fact" if case_value is None else
                "match" if case_value == confirmed_value else "conflict"
            ),
        })
    ambiguous = review.get("ambiguous_fields", [])
    conflicts = any(r["comparison"] == "conflict" for r in results)
    is_reviewed = review.get("user_reviewed") is True
    return {
        "status": (
            "unreadable" if status == "unreadable" else
            "no_supported_fields" if status == "no_supported_fields" else
            "needs_user_confirmation" if not is_reviewed else
            "needs_manual_review" if ambiguous else
            "conflict" if conflicts else
            "needs_confirmed_intake" if not intake_confirmed else
            "user_reviewed_unverified"
        ),
        "candidates": review.get("candidates", []),
        "confirmed_fields": confirmed,
        "extraction_digest": review.get("extraction_digest"),
        "comparisons": results,
        "ambiguous_fields": ambiguous,
        "user_reviewed": is_reviewed,
        "no_legal_verification": True,
        "official_submission": False,
        "document_id": document_id,
    }
