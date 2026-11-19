"""Project the status of accessible private document fields for clarification."""

from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.contract import DocumentFieldStatus
from app.cases.intake_schemas import IntakeFacts
from app.config import Settings
from app.private_documents import intelligence as intel
from app.private_documents.model import PrivateCaseDocument
from app.private_documents.security import CONSENT_VERSION, MAX_DOCS_PER_CASE, fixture_hashes, validate_release_settings


def read_document_field_statuses(
    db: Session, *, case_id: str, owner: str, facts: IntakeFacts | None, settings: Settings | None,
) -> dict[str, DocumentFieldStatus]:
    """Read review metadata after the worker has checked the linked case."""
    if settings is None or not settings.enable_private_document_api:
        return {}
    try:
        key = validate_release_settings(settings)
    except ValueError:
        return {}

    doc = PrivateCaseDocument
    query = select(doc.id, doc.review_ciphertext).where(
        doc.case_id == case_id, doc.owner_subject == owner, doc.category == "housing_document",
        doc.expires_at > datetime.now(timezone.utc), doc.consent_version == CONSENT_VERSION,
        doc.consented_at.is_not(None), doc.scanned_at.is_not(None), doc.review_ciphertext.is_not(None),
    )
    if settings.private_document_fixture_mode:
        if sha256(owner.encode()).hexdigest() not in fixture_hashes(settings.private_document_fixture_subject_hashes):
            return {}
        query = query.where(doc.content_sha256.in_(fixture_hashes(settings.private_document_fixture_file_hashes)))
    rows = db.execute(query.limit(MAX_DOCS_PER_CASE + 1)).all()
    if len(rows) > MAX_DOCS_PER_CASE:
        return {}

    needs_review: set[str] = set()
    confirmed: dict[str, set[str]] = defaultdict(set)
    for document_id, ciphertext in rows:
        try:
            review = intel.read_review_metadata(
                ciphertext, key=key, case_id=case_id, owner=owner, document_id=document_id,
            )
        except ValueError:
            continue
        if review is None or review.get("status") != "needs_user_confirmation":
            continue
        candidates = review.get("candidates")
        chosen = review.get("confirmed_fields")
        ambiguous = review.get("ambiguous_fields")
        selected = review.get("selected_evidence")
        if (not isinstance(candidates, list) or len(candidates) > intel.MAX_CANDIDATES
                or not isinstance(chosen, dict) or not isinstance(ambiguous, list) or not isinstance(selected, dict)):
            continue
        for field in intel.REVIEW_FIELDS:
            value = chosen.get(field)
            evidence_ids = {
                candidate["candidate_id"] for candidate in candidates
                if isinstance(candidate, dict) and candidate.get("field_name") == field
                and isinstance(candidate.get("candidate_id"), str)
                and isinstance(suggested := candidate.get("suggested_value"), str)
                and intel.valid_confirmation(field, suggested)
            }
            if not evidence_ids:
                continue
            evidence = selected.get(field)
            if (review.get("user_reviewed") is True and field not in ambiguous
                    and isinstance(evidence, str) and evidence in evidence_ids
                    and isinstance(value, str) and intel.valid_confirmation(field, value)):
                confirmed[field].add(value)
            else:
                needs_review.add(field)

    statuses: dict[str, DocumentFieldStatus] = {field: "needs_review" for field in needs_review}
    for field, values in confirmed.items():
        case_value = getattr(facts, field, None)
        if len(values) > 1 or (case_value is not None and case_value not in values):
            statuses[field] = "conflict"
        elif field not in needs_review:
            statuses[field] = "reviewed"
    return statuses
