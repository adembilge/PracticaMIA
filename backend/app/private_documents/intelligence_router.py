"""Opt-in owner-only extraction and review on encrypted private documents.

Only a clean-scanned, unexpired HOUSING document may be parsed locally.
The document and review metadata never leave the private vault to any LLM.
Document review does not change or confirm case intake facts or legal rules.
"""
from __future__ import annotations

import json
from hashlib import sha256
from hmac import compare_digest
from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.tokens import Principal, get_principal
from app.cases.router import get_case
from app.cases.intake_model import CaseIntake
from app.database import get_session
from app.preparation.extract import DocumentRejected, ExtractionUnavailable
from app.private_documents.model import PrivateCaseDocument
from app.private_documents.security import open_bytes, seal_bytes
from app.private_documents import intelligence as intel

def _now():
    return datetime.now(timezone.utc)


router = APIRouter(
    prefix="/api/v1/cases", tags=["private-document-intelligence"],
    dependencies=[Depends(get_principal)],
)


class ReviewedField(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    field_name: str = Field(min_length=1, max_length=40)
    candidate_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    confirmed_value: str = Field(min_length=1, max_length=40)


class ConfirmReview(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    extraction_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    selections: list[ReviewedField] = Field(min_length=1, max_length=2)
    confirm: bool


def _document(db: Session, case_id: UUID, document_id: UUID, owner: str,
              *, lock: bool = False) -> PrivateCaseDocument:
    get_case(db, case_id, owner)
    statement = select(PrivateCaseDocument).where(
        PrivateCaseDocument.id == str(document_id),
        PrivateCaseDocument.case_id == str(case_id),
        PrivateCaseDocument.owner_subject == owner,
        PrivateCaseDocument.expires_at > _now(),
    )
    result = db.scalar(statement.with_for_update() if lock else statement)
    if result is None:
        raise HTTPException(404, "Document not found or expired")
    return result


def _read_metadata(doc: PrivateCaseDocument, key: bytes) -> dict | None:
    if not doc.review_ciphertext:
        return None
    try:
        raw = open_bytes(
            doc.review_ciphertext, key=key, case_id=doc.case_id,
            owner=doc.owner_subject, document_id=doc.id + ":review",
        )
        if len(raw) > intel.MAX_REVIEW_BYTES:
            raise ValueError("Oversized review")
        value = json.loads(raw)
        if not isinstance(value, dict) or value.get("version") != intel.REVIEW_VERSION:
            raise ValueError("Unexpected review")
        return value
    except Exception:
        raise HTTPException(503, "Encrypted document review is unavailable") from None


def _write_metadata(doc: PrivateCaseDocument, data: dict, key: bytes) -> None:
    raw = json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")
    if len(raw) > intel.MAX_REVIEW_BYTES:
        raise HTTPException(422, "Too many document suggestions")
    doc.review_ciphertext = seal_bytes(
        raw, key=key, case_id=doc.case_id, owner=doc.owner_subject,
        document_id=doc.id + ":review",
    )


def _response(db: Session, doc: PrivateCaseDocument, key: bytes) -> JSONResponse:
    review = _read_metadata(doc, key)
    intake = db.scalar(select(CaseIntake).where(
        CaseIntake.case_id == doc.case_id,
        CaseIntake.owner_subject == doc.owner_subject,
    ))
    result = intel.compare_review(
        review,
        intake_facts=intake.facts if intake is not None else None,
        intake_confirmed=bool(intake is not None and intake.confirmed_at),
        document_id=doc.id,
    )
    if doc.category != "housing_document":
        result = {**result, "status": "unsupported_category",
                  "candidates": [], "confirmed_fields": {},
                  "comparisons": [], "user_reviewed": False}
    return JSONResponse(
        {**result, "no_legal_verification": True, "official_submission": False},
        headers={"Cache-Control": "private, no-store"},
    )


@router.get("/{case_id}/private-documents/{document_id}/intelligence")
def get_document_intelligence(
    case_id: UUID, document_id: UUID, request: Request,
    db: Session = Depends(get_session),
    principal: Principal = Depends(get_principal),
):
    doc = _document(db, case_id, document_id, principal.subject)
    return _response(db, doc, request.app.state.private_document_key)


@router.post("/{case_id}/private-documents/{document_id}/intelligence/extract")
def extract_private_document(
    case_id: UUID, document_id: UUID, request: Request,
    db: Session = Depends(get_session),
    principal: Principal = Depends(get_principal),
):
    doc = _document(db, case_id, document_id, principal.subject, lock=True)
    if doc.category != "housing_document":
        raise HTTPException(422, "Only housing documents have supported extractors")
    key = request.app.state.private_document_key
    previous = _read_metadata(doc, key)
    if previous is not None:
        # Idempotent; repeated clicks never trigger unbounded OCR/CPU work.
        return _response(db, doc, key)
    if not doc.scanned_at or not doc.consented_at:
        raise HTTPException(409, "Unscanned or unconsented document")
    try:
        raw = open_bytes(
            doc.ciphertext, key=key, case_id=doc.case_id,
            owner=doc.owner_subject, document_id=doc.id,
        )
        if not compare_digest(sha256(raw).hexdigest(), doc.content_sha256):
            raise ValueError("Digest mismatch")
    except Exception:
        raise HTTPException(503, "Encrypted document content is unavailable") from None
    try:
        result = intel.new_review(raw, doc.media_type, doc.content_sha256)
    except ExtractionUnavailable:
        raise HTTPException(503, "Local OCR is unavailable") from None
    except DocumentRejected:
        raise HTTPException(422, "Document could not be safely extracted") from None
    # Never save full page text, extracted address, or arbitrary model content.
    _write_metadata(doc, result, key)
    db.commit()
    return _response(db, doc, key)


@router.put("/{case_id}/private-documents/{document_id}/intelligence/review")
def confirm_private_document_review(
    case_id: UUID, document_id: UUID, payload: ConfirmReview,
    request: Request,
    db: Session = Depends(get_session),
    principal: Principal = Depends(get_principal),
):
    doc = _document(db, case_id, document_id, principal.subject, lock=True)
    if doc.category != "housing_document" or payload.confirm is not True:
        raise HTTPException(422, "Explicit confirmation is required")
    key = request.app.state.private_document_key
    previous = _read_metadata(doc, key)
    if previous is None:
        raise HTTPException(409, "Extract supported fields first")
    try:
        reviewed = intel.validate_user_review(
            previous, token=payload.extraction_digest,
            selections=[v.model_dump() for v in payload.selections],
        )
    except ValueError:
        raise HTTPException(409, "Review is stale or contains unsupported fields") from None
    _write_metadata(doc, reviewed, key)
    db.commit()
    return _response(db, doc, key)
