"""Authenticated synthetic-only preview endpoints for the P0 preparation vertical slice.

Not legal advice: official citation checks re-run on every assessment, and
nothing can become submission_ready without reviewed rules and user consent.
Production startup forbids this router regardless of feature flag input.
"""
from __future__ import annotations

import json
from hashlib import sha256
import re
from uuid import UUID, uuid4
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth.tokens import Principal, get_principal
from app.cases.router import get_case
from app.database import get_session
from app.knowledge.search import resolve_approved_passage
from app.preparation.crypto import decrypt_blob, encrypt_blob
from app.preparation.extract import (
    DocumentRejected, ExtractionUnavailable, MAX_FILE_BYTES,
    extract_document, validate_document, verify_confirmation,
)
from app.preparation.models import CaseDocument, CasePreparation
from app.preparation.intake import scope_intake, validate_scope_facts
from app.preparation.anpr_draft import build_anpr_draft
from app.preparation.agent import guide_case
from app.preparation.workflow import assess_preparation
from app.rules.catalog import current_catalog
from app.rules.engine import JURISDICTION, PROCEDURE

router = APIRouter(
    prefix="/api/v1/cases", tags=["synthetic-preparation-preview"],
    dependencies=[Depends(get_principal)],
)
CATEGORY_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
# Exact, reviewed source-passage candidates for general background only.
# These IDs never activate an administrative rule or a package.
REFERENCE_PASSAGES = (
    "e139e910-3a89-4994-b450-b5107d8db7dd:0000",
    "e139e910-3a89-4994-b450-b5107d8db7dd:0003",
    "e139e910-3a89-4994-b450-b5107d8db7dd:0005",
)


class GuideRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=2, max_length=180)
    language: Literal["en", "it"] = "en"


class FactsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmed_facts: dict[str, str | int | bool] = Field(max_length=48)


class FieldConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field_name: str = Field(min_length=1, max_length=64)
    raw_value: str = Field(min_length=1, max_length=180)
    confirmed_value: str = Field(min_length=1, max_length=180)
    page: int = Field(ge=1, le=15)


class DocumentReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirm_document: bool


class PackageApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")
    review_digest: str = Field(pattern=r"^[a-f0-9]{64}$")


def _key(request: Request) -> bytes:
    return request.app.state.preparation_document_key


def _case(db: Session, case_id: UUID, principal: Principal):
    case = get_case(db, case_id, principal.subject)
    if case.procedure != PROCEDURE:
        raise HTTPException(422, "Unsupported preparation procedure")
    return case


def _preparation(db: Session, case_id: str, owner: str) -> CasePreparation | None:
    return db.scalar(select(CasePreparation).where(
        CasePreparation.case_id == case_id,
        CasePreparation.owner_subject == owner,
    ))


def _encrypted_json(data: dict, *, request: Request, case_id: str,
                    owner: str, name: str) -> bytes:
    raw = json.dumps(data, sort_keys=True, ensure_ascii=False,
                     separators=(",", ":")).encode("utf-8")
    return encrypt_blob(raw, key=_key(request), case_id=case_id,
                        owner_subject=owner, document_id=name)


def _decrypted_json(blob: bytes, *, request: Request, case_id: str,
                    owner: str, name: str) -> dict:
    if not blob:
        return {}
    # Authenticated encryption already checks tampering; sha256 would be
    # redundant for this internal JSON payload.
    try:
        if len(blob) < 29:
            raise ValueError("Short encrypted metadata")
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from app.preparation.crypto import associated_data
        raw = AESGCM(_key(request)).decrypt(
            blob[:12], blob[12:], associated_data(case_id, owner, name),
        )
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            raise ValueError("Private record is not a map")
        return obj
    except Exception:
        # Never leak ciphertext, parsing errors, or sensitive values.
        raise HTTPException(503, "Private case material is unavailable") from None


def _facts(request: Request, row: CasePreparation | None,
           case_id: str, owner: str) -> dict:
    return _decrypted_json(row.facts_ciphertext, request=request, case_id=case_id,
                           owner=owner, name="case-facts") if row else {}


def _review(request: Request, doc: CaseDocument) -> dict:
    return _decrypted_json(
        doc.review_ciphertext, request=request, case_id=doc.case_id,
        owner=doc.owner_subject, name=f"{doc.id}:review",
    )


def _document(db: Session, case_id: str, owner: str,
              document_id: UUID) -> CaseDocument:
    doc = db.scalar(select(CaseDocument).where(
        CaseDocument.id == str(document_id),
        CaseDocument.case_id == case_id,
        CaseDocument.owner_subject == owner,
    ))
    if doc is None:
        raise HTTPException(404, "Document not found")
    return doc


def _summary(request: Request, doc: CaseDocument) -> dict:
    review = _review(request, doc)
    extraction = review.get("extraction", {})
    return {
        "id": doc.id,
        "document_type": doc.document_type,
        "media_type": doc.media_type,
        "sha256": doc.content_sha256,
        "extraction_status": extraction.get("status", "not_processed"),
        "candidates": extraction.get("candidates", []),
        "confirmed_fields": review.get("confirmed_fields", {}),
        "status": "confirmed" if review.get("confirmed_document") is True else
                  extraction.get("status", "uploaded"),
    }


def _assessment(db: Session, request: Request, case_id: str, owner: str) -> dict:
    prep = _preparation(db, case_id, owner)
    docs = db.scalars(select(CaseDocument).where(
        CaseDocument.case_id == case_id,
        CaseDocument.owner_subject == owner,
    ).order_by(CaseDocument.id)).all()
    summaries = [_summary(request, doc) for doc in docs]

    def citation_approved(citation_id: str) -> bool:
        return resolve_approved_passage(
            db, citation_id=citation_id, jurisdiction=JURISDICTION,
            procedure_id=PROCEDURE, language="it",
        ) is not None

    return assess_preparation(
        case_id=case_id, facts=_facts(request, prep, case_id, owner),
        catalog=current_catalog(), citation_is_approved=citation_approved,
        documents=summaries,
    )


@router.get("/{case_id}/preparation")
def read_preparation(case_id: UUID, request: Request,
                     db: Session = Depends(get_session),
                     principal: Principal = Depends(get_principal)):
    _case(db, case_id, principal)
    case_id_str = str(case_id)
    prep = _preparation(db, case_id_str, principal.subject)
    result = _assessment(db, request, case_id_str, principal.subject)
    saved_facts = _facts(request, prep, case_id_str, principal.subject)
    # Scope matching is neither legal eligibility nor an approved requirements check.
    return {
        "is_demo": True,
        "confirmed_facts": saved_facts,
        "intake": scope_intake(saved_facts),
        "workflow": result,
        "user_reviewed": bool(
            result["package"] and prep and
            prep.review_digest == result["package"]["review_digest"]
        ),
    }


@router.put("/{case_id}/preparation/facts")
def replace_facts(case_id: UUID, payload: FactsUpdate, request: Request,
                  db: Session = Depends(get_session),
                  principal: Principal = Depends(get_principal)):
    _case(db, case_id, principal)
    values = payload.confirmed_facts
    if not validate_scope_facts(values) or any(
        not CATEGORY_RE.fullmatch(key) or
        (isinstance(value, str) and (not value.strip() or len(value) > 240))
        for key, value in values.items()
    ):
        raise HTTPException(422, "Invalid confirmed fact fields")
    current = _preparation(db, str(case_id), principal.subject)
    if current is None:
        current = CasePreparation(case_id=str(case_id), owner_subject=principal.subject)
        db.add(current)
    current.facts_ciphertext = _encrypted_json(
        values, request=request, case_id=str(case_id),
        owner=principal.subject, name="case-facts",
    )
    current.review_digest = None
    db.commit()
    return {"status": "saved", "is_demo": True, "confirmed_fact_count": len(values)}




@router.get("/{case_id}/preparation/anpr-draft")
def read_anpr_draft(
    case_id: UUID, request: Request,
    db: Session = Depends(get_session),
    principal: Principal = Depends(get_principal),
):
    """Owner-scoped saved-fact transcription; never an official application."""
    _case(db, case_id, principal)
    row = _preparation(db, str(case_id), principal.subject)
    return build_anpr_draft(
        _facts(request, row, str(case_id), principal.subject)
    )


@router.get("/{case_id}/preparation/reference-evidence")
def read_reference_evidence(
    case_id: UUID, request: Request,
    db: Session = Depends(get_session),
    principal: Principal = Depends(get_principal),
):
    """Owner-scoped excerpts, not unreviewed requirements or legal assessment."""
    _case(db, case_id, principal)
    references = []
    for citation_id in REFERENCE_PASSAGES:
        passage = resolve_approved_passage(
            db, citation_id=citation_id, jurisdiction=JURISDICTION,
            procedure_id=PROCEDURE, language="it",
        )
        if passage is None:
            continue  # A changed or revoked source must disappear immediately.
        reviewed = passage.reviewed_at
        references.append({
            "citation_id": citation_id,
            "title": passage.title,
            "official_url": passage.official_url,
            "excerpt": passage.content[:1000],
            "reviewed_at": reviewed.isoformat() if hasattr(reviewed, "isoformat") else str(reviewed),
        })
    return {
        "status": "reference_only" if len(references) == len(REFERENCE_PASSAGES)
                  else "partial_or_unavailable",
        "references": references,
        "personalized_requirements": False,
        "is_demo": True,
    }

@router.post("/{case_id}/preparation/guide")
def guide_case_preview(
    case_id: UUID, payload: GuideRequest, request: Request,
    db: Session = Depends(get_session),
    principal: Principal = Depends(get_principal),
):
    """Bounded tool selection: model sees only the user's short fictional question.

    Tool callbacks run with an authenticated owner and current source approvals.
    An LLM cannot write case facts, activate rules or invent an application.
    """
    _case(db, case_id, principal)
    settings = request.app.state.settings
    model = None
    if settings.enable_assistant_api:
        # This flag enforces existing preview-only provider and usage controls.
        from app.knowledge.assistant_router import _model_for_preview
        from app.knowledge.usage_limit import reserve_daily_model_call
        try:
            model = _model_for_preview(request)
        except Exception:
            model = None
        if model is not None and not reserve_daily_model_call(
            db, subject=principal.subject,
            hash_key=settings.assistant_usage_hash_key,
            daily_limit=settings.assistant_daily_limit,
        ):
            raise HTTPException(429, "Daily preview model limit reached")

    def evidence_tool() -> list[dict]:
        # Reuse the approval-filtered, owner-scoped endpoint contract.
        return read_reference_evidence(
            case_id=case_id, request=request, db=db, principal=principal,
        )["references"]

    def status_tool() -> dict:
        return _assessment(db, request, str(case_id), principal.subject)

    prep = _preparation(db, str(case_id), principal.subject)
    return guide_case(
        question=payload.question, language=payload.language,
        facts=_facts(request, prep, str(case_id), principal.subject),
        evidence_tool=evidence_tool, status_tool=status_tool, model=model,
    )


@router.get("/{case_id}/preparation/checklist")
def read_checklist(case_id: UUID, request: Request,
                   db: Session = Depends(get_session),
                   principal: Principal = Depends(get_principal)):
    _case(db, case_id, principal)
    result = _assessment(db, request, str(case_id), principal.subject)
    return {"decision": result["rules"]["decision"],
            "checklist": result["rules"]["checklist"],
            "missing_fields": result["rules"]["missing_fields"],
            "evidence_refs": result["rules"]["evidence_refs"],
            "blocking_issues": result["blocking_issues"], "is_demo": True}


@router.post("/{case_id}/preparation/documents", status_code=201)
async def upload_document(
    case_id: UUID, request: Request, document_type: str = Form(...),
    file: UploadFile = File(...),
    synthetic_ack: str = Header(default="", alias="X-PracticaMIA-Synthetic-Only"),
    db: Session = Depends(get_session),
    principal: Principal = Depends(get_principal),
):
    _case(db, case_id, principal)
    if synthetic_ack != "YES":
        raise HTTPException(403, "Preview accepts synthetic fixture data only")
    if not CATEGORY_RE.fullmatch(document_type):
        raise HTTPException(422, "Invalid document category")
    try:
        body = await file.read(MAX_FILE_BYTES + 1)
        validate_document(body, file.content_type or "")
    except DocumentRejected as exc:
        raise HTTPException(422, str(exc)) from None
    finally:
        await file.close()
    doc_id = str(uuid4())
    doc = CaseDocument(
        id=doc_id, case_id=str(case_id), owner_subject=principal.subject,
        document_type=document_type, media_type=file.content_type,
        content_sha256=sha256(body).hexdigest(),
        ciphertext=encrypt_blob(
            body, key=_key(request), case_id=str(case_id),
            owner_subject=principal.subject, document_id=doc_id,
        ),
        review_ciphertext=b"",
    )
    db.add(doc)
    prep = _preparation(db, str(case_id), principal.subject)
    if prep:
        prep.review_digest = None
    db.commit()
    return _summary(request, doc)


@router.get("/{case_id}/preparation/documents")
def list_documents(case_id: UUID, request: Request,
                   db: Session = Depends(get_session),
                   principal: Principal = Depends(get_principal)):
    _case(db, case_id, principal)
    docs = db.scalars(select(CaseDocument).where(
        CaseDocument.case_id == str(case_id),
        CaseDocument.owner_subject == principal.subject,
    )).all()
    return [_summary(request, doc) for doc in docs]


@router.post("/{case_id}/preparation/documents/{document_id}/extract")
def extract_saved_document(
    case_id: UUID, document_id: UUID, request: Request,
    db: Session = Depends(get_session),
    principal: Principal = Depends(get_principal),
):
    _case(db, case_id, principal)
    doc = _document(db, str(case_id), principal.subject, document_id)
    try:
        original = decrypt_blob(
            doc.ciphertext, key=_key(request), case_id=doc.case_id,
            owner_subject=doc.owner_subject, document_id=doc.id,
            expected_digest=doc.content_sha256,
        )
        extraction = extract_document(original, doc.media_type)
    except ExtractionUnavailable as exc:
        raise HTTPException(503, str(exc)) from None
    except (DocumentRejected, ValueError):
        raise HTTPException(422, "Document cannot be safely extracted") from None
    except Exception:
        raise HTTPException(503, "Document storage integrity check failed") from None
    doc.review_ciphertext = _encrypted_json(
        {"extraction": extraction, "confirmed_fields": {},
         "confirmed_document": False},
        request=request, case_id=doc.case_id, owner=doc.owner_subject,
        name=f"{doc.id}:review",
    )
    prep = _preparation(db, str(case_id), principal.subject)
    if prep:
        prep.review_digest = None
    db.commit()
    # Do not return raw extracted pages in a broad list API; candidates contain
    # only small evidence spans and must still be confirmed by the user.
    return _summary(request, doc)


@router.post("/{case_id}/preparation/documents/{document_id}/confirm-fields")
def confirm_extracted_field(
    case_id: UUID, document_id: UUID, payload: FieldConfirmation,
    request: Request, db: Session = Depends(get_session),
    principal: Principal = Depends(get_principal),
):
    _case(db, case_id, principal)
    doc = _document(db, str(case_id), principal.subject, document_id)
    review = _review(request, doc)
    try:
        verify_confirmation(review.get("extraction", {}), payload.field_name,
                            payload.raw_value, payload.page)
    except DocumentRejected as exc:
        raise HTTPException(422, str(exc)) from None
    confirmed = review.get("confirmed_fields", {})
    confirmed[payload.field_name] = payload.confirmed_value
    review.update(confirmed_fields=confirmed, confirmed_document=False)
    doc.review_ciphertext = _encrypted_json(
        review, request=request, case_id=doc.case_id,
        owner=doc.owner_subject, name=f"{doc.id}:review",
    )
    prep = _preparation(db, str(case_id), principal.subject)
    if prep:
        prep.review_digest = None
    db.commit()
    return _summary(request, doc)


@router.post("/{case_id}/preparation/documents/{document_id}/review")
def review_extracted_document(
    case_id: UUID, document_id: UUID, payload: DocumentReview,
    request: Request, db: Session = Depends(get_session),
    principal: Principal = Depends(get_principal),
):
    _case(db, case_id, principal)
    doc = _document(db, str(case_id), principal.subject, document_id)
    review = _review(request, doc)
    extraction = review.get("extraction", {})
    if payload.confirm_document is not True:
        raise HTTPException(422, "Document review requires affirmative user confirmation")
    if extraction.get("status") != "needs_user_confirmation":
        raise HTTPException(409, "Document requires a readable extraction")
    fields = {v["field_name"] for v in extraction.get("candidates", [])}
    if not fields.issubset(set(review.get("confirmed_fields", {}))):
        raise HTTPException(409, "Confirm or correct extracted fields before document review")
    review["confirmed_document"] = True
    doc.review_ciphertext = _encrypted_json(
        review, request=request, case_id=doc.case_id,
        owner=doc.owner_subject, name=f"{doc.id}:review",
    )
    prep = _preparation(db, str(case_id), principal.subject)
    if prep:
        prep.review_digest = None
    db.commit()
    return _summary(request, doc)


@router.delete("/{case_id}/preparation/documents/{document_id}", status_code=204)
def delete_document(
    case_id: UUID, document_id: UUID, request: Request,
    db: Session = Depends(get_session),
    principal: Principal = Depends(get_principal),
):
    _case(db, case_id, principal)
    doc = _document(db, str(case_id), principal.subject, document_id)
    db.delete(doc)
    prep = _preparation(db, str(case_id), principal.subject)
    if prep:
        prep.review_digest = None
    db.commit()


@router.get("/{case_id}/preparation/package")
def review_package(case_id: UUID, request: Request,
                   db: Session = Depends(get_session),
                   principal: Principal = Depends(get_principal)):
    _case(db, case_id, principal)
    result = _assessment(db, request, str(case_id), principal.subject)
    return {
        "status": result["status"],
        "blocking_issues": result["blocking_issues"],
        "package": result["package"],
        "is_demo": True,
        "no_government_submission": True,
    }


@router.post("/{case_id}/preparation/package/approve")
def approve_reviewed_package(
    case_id: UUID, payload: PackageApproval, request: Request,
    db: Session = Depends(get_session),
    principal: Principal = Depends(get_principal),
):
    _case(db, case_id, principal)
    result = _assessment(db, request, str(case_id), principal.subject)
    package = result["package"]
    if not package or package["review_digest"] != payload.review_digest:
        raise HTTPException(409, "Package blocked or changed since user review")
    prep = _preparation(db, str(case_id), principal.subject)
    if prep is None:
        raise HTTPException(409, "No confirmed case facts")
    prep.review_digest = package["review_digest"]
    db.commit()
    # Internal readiness is never a government submission or acceptance.
    return {"status": "submission_ready", "is_demo": True,
            "no_government_submission": True,
            "review_digest": prep.review_digest}


@router.get("/{case_id}/preparation/handoff")
def official_handoff(
    case_id: UUID, request: Request, db: Session = Depends(get_session),
    principal: Principal = Depends(get_principal),
):
    _case(db, case_id, principal)
    result = _assessment(db, request, str(case_id), principal.subject)
    prep = _preparation(db, str(case_id), principal.subject)
    package = result["package"]
    if not package or prep is None or prep.review_digest != package["review_digest"]:
        raise HTTPException(409, "User-reviewed package and valid sources required")
    links = []
    for ref in result["rules"]["evidence_refs"]:
        passage = resolve_approved_passage(
            db, citation_id=ref, jurisdiction=JURISDICTION,
            procedure_id=PROCEDURE, language="it",
        )
        if passage is None:
            raise HTTPException(409, "A required official source is no longer approved")
        links.append({"title": passage.title, "official_url": passage.official_url,
                      "citation_id": ref, "reviewed_at": passage.reviewed_at})
    return {"status": "user_handoff", "links": links,
            "instructions": "Open the verified official source and submit yourself; PracticaMIA does not submit.",
            "is_demo": True, "government_status": "not_submitted"}
