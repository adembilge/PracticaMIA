"""Authenticated document vault, deliberately independent of preview preparation.

This route stores only scanned, consented and encrypted bytes. No OCR, AI,
official submission, eligibility decision, or plaintext retrieval endpoint.
"""
from datetime import datetime, timezone
from hashlib import sha256
from hmac import compare_digest
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.auth.tokens import Principal, get_principal
from app.cases.model import CaseRecord
from app.cases.router import get_case
from app.database import get_session
from app.preparation.extract import DocumentRejected, MAX_FILE_BYTES, validate_document
from app.private_documents.model import PrivateCaseDocument
from app.private_documents.security import (
    CONSENT_VERSION, DOC_CATEGORIES, MAX_DOCS_PER_CASE,
    MalwareDetected, ScanUnavailable, expiry_from,
    scan_bytes, seal_bytes, validate_private_file,
)

router = APIRouter(
    prefix="/api/v1/cases", tags=["private-documents"],
    dependencies=[Depends(get_principal)],
)
retention_router = APIRouter(tags=["private-document-retention"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _summary(doc: PrivateCaseDocument) -> dict:
    return {
        "id": doc.id,
        "category": doc.category,
        "media_type": doc.media_type,
        "uploaded_at": doc.uploaded_at.isoformat(),
        "expires_at": doc.expires_at.isoformat(),
        "retention_days": 7,
        "review_status": "stored_unverified",
        "official_submission": False,
    }


@router.post("/{case_id}/private-documents", status_code=201)
async def add_private_document(
    case_id: UUID, request: Request,
    category: str = Form(...),
    privacy_ack: bool = Form(False),
    consent_version: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
    principal: Principal = Depends(get_principal),
):
    get_case(db, case_id, principal.subject)
    if privacy_ack is not True or consent_version != CONSENT_VERSION:
        raise HTTPException(422, "Review and accept the current document privacy notice")
    if category not in DOC_CATEGORIES:
        raise HTTPException(422, "Unsupported document category")
    if request.headers.get("content-length"):
        try:
            if int(request.headers["content-length"]) > MAX_FILE_BYTES + 4096:
                raise HTTPException(413, "Upload too large")
        except ValueError:
            raise HTTPException(413, "Invalid request size") from None

    try:
        body = await file.read(MAX_FILE_BYTES + 1)
        validate_document(body, file.content_type or "")
    except DocumentRejected as exc:
        raise HTTPException(422, str(exc)) from None
    finally:
        await file.close()

    # Infected/unavailable scanners always fail closed, before storing bytes.
    try:
        scan_bytes(body, request.app.state.settings)
        validate_private_file(body, file.content_type or "")
    except MalwareDetected:
        raise HTTPException(422, "Upload rejected by document security scan") from None
    except ScanUnavailable:
        raise HTTPException(503, "Document security scan is unavailable") from None
    except DocumentRejected as exc:
        raise HTTPException(422, str(exc)) from None

    case_str = str(case_id)
    now = _now()
    # Serialise concurrent uploads for one case on PostgreSQL.
    locked = db.scalar(select(CaseRecord).where(
        CaseRecord.id == case_str, CaseRecord.owner_subject == principal.subject,
    ).with_for_update())
    if locked is None:
        raise HTTPException(404, "Case not found")
    # Expired documents cannot count against the per-case limit.
    db.execute(delete(PrivateCaseDocument).where(
        PrivateCaseDocument.case_id == case_str,
        PrivateCaseDocument.owner_subject == principal.subject,
        PrivateCaseDocument.expires_at <= now,
    ))
    count = db.scalar(select(func.count()).select_from(PrivateCaseDocument).where(
        PrivateCaseDocument.case_id == case_str,
        PrivateCaseDocument.owner_subject == principal.subject,
        PrivateCaseDocument.expires_at > now,
    ))
    if count is None or count >= MAX_DOCS_PER_CASE:
        raise HTTPException(429, "Document limit reached for this case")
    document_id = str(uuid4())
    record = PrivateCaseDocument(
        id=document_id,
        case_id=case_str,
        owner_subject=principal.subject,
        category=category,
        media_type=file.content_type,
        content_sha256=sha256(body).hexdigest(),
        ciphertext=seal_bytes(
            body, key=request.app.state.private_document_key,
            case_id=case_str, owner=principal.subject, document_id=document_id,
        ),
        consent_version=CONSENT_VERSION,
        consented_at=now,
        scanned_at=now,
        uploaded_at=now,
        expires_at=expiry_from(now),
    )
    db.add(record)
    db.commit()
    return JSONResponse(_summary(record), status_code=201,
                        headers={"Cache-Control": "private, no-store"})


@router.get("/{case_id}/private-documents")
def list_private_documents(
    case_id: UUID, db: Session = Depends(get_session),
    principal: Principal = Depends(get_principal),
):
    get_case(db, case_id, principal.subject)
    docs = db.scalars(select(PrivateCaseDocument).where(
        PrivateCaseDocument.case_id == str(case_id),
        PrivateCaseDocument.owner_subject == principal.subject,
        PrivateCaseDocument.expires_at > _now(),
    ).order_by(PrivateCaseDocument.uploaded_at.desc()).limit(MAX_DOCS_PER_CASE)).all()
    return JSONResponse([_summary(doc) for doc in docs],
                        headers={"Cache-Control": "private, no-store"})


@router.delete("/{case_id}/private-documents/{document_id}", status_code=204)
def delete_private_document(
    case_id: UUID, document_id: UUID,
    db: Session = Depends(get_session),
    principal: Principal = Depends(get_principal),
):
    get_case(db, case_id, principal.subject)
    result = db.execute(delete(PrivateCaseDocument).where(
        PrivateCaseDocument.id == str(document_id),
        PrivateCaseDocument.case_id == str(case_id),
        PrivateCaseDocument.owner_subject == principal.subject,
    ))
    if not result.rowcount:
        raise HTTPException(404, "Document not found")
    db.commit()


@retention_router.get("/internal/retention/purge", include_in_schema=False)
def purge_expired_documents(
    request: Request,
    db: Session = Depends(get_session),
):
    """For Vercel Cron. Erase expired encrypted content in bounded batches.

    Do not assume this removes old Neon backup/PITR copies. Operations must
    monitor the scheduled function; a disabled or failed cron is not retention.
    """
    secret = request.app.state.settings.private_document_cron_secret
    expected = "Bearer " + secret
    received = request.headers.get("authorization", "")
    if not secret or not compare_digest(received, expected):
        raise HTTPException(401, "Unauthorized")
    now = _now()
    rows = db.scalars(select(PrivateCaseDocument.id).where(
        PrivateCaseDocument.expires_at <= now,
    ).order_by(PrivateCaseDocument.expires_at).limit(500)).all()
    if rows:
        db.execute(delete(PrivateCaseDocument).where(PrivateCaseDocument.id.in_(rows)))
        db.commit()
    more = db.scalar(select(PrivateCaseDocument.id).where(
        PrivateCaseDocument.expires_at <= now,
    ).limit(1)) is not None
    return JSONResponse({"purged": len(rows), "more_expired": more},
                        headers={"Cache-Control": "no-store"})
