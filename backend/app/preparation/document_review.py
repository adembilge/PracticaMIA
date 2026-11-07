"""Deterministic owner-scoped document review for the synthetic MVP Preview.

This checks *confirmed* user and document values only. OCR candidates cannot be
treated as facts, and a clean result never represents an approved administrative
requirements check or government acceptance.
"""
from __future__ import annotations

from typing import Any


def _text(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return " ".join(value.split()).casefold()


def inspect_documents(*, facts: dict, documents: list[dict]) -> dict:
    """Summarize review work and confirmed-value disagreements, even if rules block.

    The response intentionally contains no extracted values or full document text.
    Callers may only expose it behind existing case-owner authorization.
    """
    needs_extraction: list[str] = []
    needs_confirmation: list[str] = []
    needs_review: list[str] = []
    unreadable: list[str] = []
    conflicts: list[dict[str, Any]] = []
    first_document_value: dict[str, tuple[str, str]] = {}

    for doc in documents:
        document_id = doc.get("id", "")
        if not isinstance(document_id, str) or not document_id:
            continue
        status = doc.get("status")
        extraction_status = doc.get("extraction_status", status)
        confirmed_fields = doc.get("confirmed_fields") or {}
        if not isinstance(confirmed_fields, dict):
            confirmed_fields = {}

        if status == "unreadable" or extraction_status == "unreadable":
            unreadable.append(document_id)
        elif status == "confirmed":
            pass
        elif extraction_status in ("uploaded", "not_processed", None):
            needs_extraction.append(document_id)
        elif extraction_status == "needs_user_confirmation":
            candidates = doc.get("candidates") or []
            candidate_fields = {
                candidate.get("field_name") for candidate in candidates
                if isinstance(candidate, dict) and isinstance(candidate.get("field_name"), str)
            }
            if candidate_fields - set(confirmed_fields):
                needs_confirmation.append(document_id)
            else:
                needs_review.append(document_id)
        else:
            # Unknown state is not silently accepted as reviewed.
            needs_review.append(document_id)

        # Only explicitly user-confirmed strings participate in comparisons.
        for field, raw in sorted(confirmed_fields.items()):
            if not isinstance(field, str):
                continue
            value = _text(raw)
            if value is None:
                continue
            fact = _text(facts.get(field))
            if fact is not None and value != fact:
                conflicts.append({
                    "kind": "case_document_mismatch",
                    "field": field,
                    "document_ids": [document_id],
                })
            previous = first_document_value.get(field)
            if previous is None:
                first_document_value[field] = (value, document_id)
            elif previous[0] != value:
                conflicts.append({
                    "kind": "cross_document_mismatch",
                    "field": field,
                    "document_ids": sorted([previous[1], document_id]),
                })

    # A pending rule catalog does not suppress factual review problems, but
    # this result cannot independently authorize a package or legal guidance.
    status = (
        "conflict" if conflicts else
        "unreadable" if unreadable else
        "needs_extraction" if needs_extraction else
        "needs_confirmation" if needs_confirmation else
        "needs_review" if needs_review else
        "verified" if documents else "no_documents"
    )
    return {
        "status": status,
        "document_count": len(documents),
        "conflicts": conflicts,
        "needs_extraction": sorted(set(needs_extraction)),
        "needs_confirmation": sorted(set(needs_confirmation)),
        "needs_review": sorted(set(needs_review)),
        "unreadable": sorted(set(unreadable)),
        "not_legal_validation": True,
    }
