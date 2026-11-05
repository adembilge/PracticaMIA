"""Restricted knowledge review API; no browser-facing admin UI.

All reviewers are configured by a server-side allowlist of verified Auth0
subject IDs. Tokens cannot self-assert reviewer permissions via request claims.
"""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.tokens import Principal, get_principal
from app.database import get_session
from app.knowledge.model import KnowledgeSource, KnowledgeSourceVersion
from app.knowledge.review_model import KnowledgeReviewEvent
from app.knowledge.review_service import (
    ReviewConflict, ReviewNotFound, approve_version, revoke_version,
)
from app.knowledge.snapshot_model import KnowledgePassage, KnowledgeSnapshot
from app.knowledge.snapshots import verify_snapshot


def require_reviewer(
    request: Request, principal: Principal = Depends(get_principal),
) -> Principal:
    """A verified user is not automatically a reviewer."""
    if principal.subject not in request.app.state.settings.knowledge_reviewer_subjects:
        raise HTTPException(status_code=403, detail="Reviewer access required")
    return principal


router = APIRouter(
    prefix="/api/v1/knowledge/review",
    tags=["knowledge-review"],
    dependencies=[Depends(require_reviewer)],
)


class ReviewSummary(BaseModel):
    source_id: str
    version_id: str
    revision: int
    source_status: str
    version_status: str
    title: str
    institution: str
    jurisdiction: str
    official_url: str
    content_sha256: str
    retrieved_at: datetime


class ReviewPassage(BaseModel):
    id: str
    ordinal: int
    section_path: str
    start_offset: int
    end_offset: int
    content: str
    content_sha256: str


class ReviewPreview(ReviewSummary):
    normalized_text: str
    passages: list[ReviewPassage]
    integrity_verified: bool


class ReviewDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    review_note: str = Field(min_length=20, max_length=500)


class ReviewDecisionResponse(BaseModel):
    source_id: str
    version_id: str
    source_status: str
    version_status: str
    audit_id: str


class AuditEventView(BaseModel):
    id: str
    source_id: str
    version_id: str
    action: str
    actor_subject: str
    reason: str
    content_sha256: str
    old_source_status: str
    new_source_status: str
    old_version_status: str
    new_version_status: str
    occurred_at: datetime


def _summary(source: KnowledgeSource, version: KnowledgeSourceVersion):
    return ReviewSummary(
        source_id=source.id, version_id=version.id, revision=version.revision,
        source_status=source.status, version_status=version.status,
        title=source.title, institution=source.institution,
        jurisdiction=source.jurisdiction, official_url=source.official_url,
        content_sha256=version.content_sha256, retrieved_at=version.retrieved_at,
    )


@router.get("/queue", response_model=list[ReviewSummary])
def review_queue(db: Session = Depends(get_session)) -> list[ReviewSummary]:
    """Only versions awaiting a human decision; never used as trusted RAG."""
    rows = db.execute(
        select(KnowledgeSource, KnowledgeSourceVersion)
        .join(KnowledgeSourceVersion,
              KnowledgeSource.id == KnowledgeSourceVersion.source_id)
        .where(KnowledgeSource.status == "candidate")
        .where(KnowledgeSourceVersion.status == "pending_review")
        .order_by(KnowledgeSourceVersion.retrieved_at.desc())
        .limit(100)
    ).all()
    return [_summary(source, version) for source, version in rows]


@router.get("/versions/{version_id}", response_model=ReviewPreview)
def review_preview(
    version_id: UUID, db: Session = Depends(get_session),
):
    """Review plain extracted text and passage offsets; do not render raw HTML."""
    version = db.get(KnowledgeSourceVersion, str(version_id))
    if version is None:
        raise HTTPException(404, "Source version not found")
    source = db.get(KnowledgeSource, version.source_id)
    snapshot = db.get(KnowledgeSnapshot, version.id)
    if source is None or snapshot is None:
        raise HTTPException(404, "Source snapshot not found")
    if snapshot.fetched_url != source.official_url or not verify_snapshot(db, version):
        raise HTTPException(409, "Source snapshot failed integrity validation")
    passages = db.scalars(
        select(KnowledgePassage).where(KnowledgePassage.version_id == version.id)
        .order_by(KnowledgePassage.ordinal)
    ).all()
    summary = _summary(source, version).model_dump()
    return ReviewPreview(
        **summary, normalized_text=snapshot.normalized_text,
        passages=[ReviewPassage(
            id=p.id, ordinal=p.ordinal, section_path=p.section_path,
            start_offset=p.start_offset, end_offset=p.end_offset,
            content=p.content, content_sha256=p.content_sha256,
        ) for p in passages], integrity_verified=True,
    )


def _decision(
    *, decision: str, version_id: UUID, payload: ReviewDecision,
    principal: Principal, db: Session,
) -> ReviewDecisionResponse:
    if not payload.review_note.strip() or len(payload.review_note.strip()) < 20:
        raise HTTPException(422, "A meaningful review note is required")
    try:
        with db.begin():
            operation = approve_version if decision == "approve" else revoke_version
            result = operation(
                db, version_id=str(version_id),
                expected_digest=payload.expected_sha256,
                actor_subject=principal.subject,
                reason=payload.review_note.strip(),
            )
    except ReviewNotFound:
        raise HTTPException(404, "Source version not found") from None
    except ReviewConflict as exc:
        raise HTTPException(409, str(exc)) from None
    return ReviewDecisionResponse(**result.__dict__)


@router.post("/versions/{version_id}/approve", response_model=ReviewDecisionResponse)
def approve(
    version_id: UUID, payload: ReviewDecision,
    principal: Principal = Depends(require_reviewer),
    db: Session = Depends(get_session),
):
    return _decision(
        decision="approve", version_id=version_id, payload=payload,
        principal=principal, db=db,
    )


@router.post("/versions/{version_id}/revoke", response_model=ReviewDecisionResponse)
def revoke(
    version_id: UUID, payload: ReviewDecision,
    principal: Principal = Depends(require_reviewer),
    db: Session = Depends(get_session),
):
    return _decision(
        decision="revoke", version_id=version_id, payload=payload,
        principal=principal, db=db,
    )


class BrowserQueueItem(BaseModel):
    source_id: str
    title: str
    version_id: str
    content_sha256: str
    official_url: str
    observed_url: str
    observed_last_updated: str
    captured_text_preview: str
    integrity_verified: bool


class BrowserBatchApprovalItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=96)
    version_id: UUID
    expected_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class BrowserBatchDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[BrowserBatchApprovalItem] = Field(min_length=1, max_length=15)
    review_note: str = Field(min_length=30, max_length=500)
    confirmed_source_review: bool


@router.get("/browser-queue", response_model=list[BrowserQueueItem])
def browser_review_queue(
    db: Session = Depends(get_session),
) -> list[BrowserQueueItem]:
    """Reviewer-only mobile-friendly summaries; no PDF can appear here."""
    rows = db.execute(
        select(KnowledgeSource, KnowledgeSourceVersion, KnowledgeSnapshot)
        .join(KnowledgeSourceVersion,
              KnowledgeSource.id == KnowledgeSourceVersion.source_id)
        .join(KnowledgeSnapshot,
              KnowledgeSnapshot.version_id == KnowledgeSourceVersion.id)
        .where(KnowledgeSource.status == "candidate")
        .where(KnowledgeSourceVersion.status == "pending_review")
        .where(KnowledgeSnapshot.capture_method == "browser_rendered_text")
        .order_by(KnowledgeSource.title.asc(), KnowledgeSourceVersion.id.asc())
        .limit(50)
    ).all()
    return [
        BrowserQueueItem(
            source_id=source.id, title=source.title,
            version_id=version.id, content_sha256=version.content_sha256,
            official_url=source.official_url,
            observed_url=snapshot.observed_url or "",
            observed_last_updated=snapshot.observed_last_updated or "",
            captured_text_preview=snapshot.normalized_text[:500],
            integrity_verified=verify_snapshot(db, version),
        )
        for source, version, snapshot in rows
    ]


@router.post(
    "/approve-browser-batch", response_model=list[ReviewDecisionResponse],
)
def approve_browser_batch(
    payload: BrowserBatchDecision,
    request: Request,
    principal: Principal = Depends(require_reviewer),
    db: Session = Depends(get_session),
) -> list[ReviewDecisionResponse]:
    """Atomic reviewer-authenticated approval for explicitly examined articles.

    Only available in preview/development, never production; requires the
    same verified JWT and server-side reviewer allowlist as individual review.
    Does not allow historical PDF versions or uninspected source substitutions.
    A failed version/hash leaves ALL earlier approvals rolled back.
    """
    if request.app.state.settings.deployment_environment == "production":
        raise HTTPException(404, "Not found")
    if not payload.confirmed_source_review:
        raise HTTPException(422, "Explicit source review attestation required")
    if len(payload.review_note.strip()) < 30:
        raise HTTPException(422, "A meaningful review note is required")
    source_ids = [item.source_id for item in payload.items]
    version_ids = [str(item.version_id) for item in payload.items]
    if len(set(source_ids)) != len(source_ids) or len(set(version_ids)) != len(version_ids):
        raise HTTPException(422, "Duplicate source or version in approval batch")

    try:
        with db.begin():
            results = []
            # Lock in stable source-ID order and approve within one transaction.
            for item in sorted(payload.items, key=lambda x: x.source_id):
                version = db.get(KnowledgeSourceVersion, str(item.version_id))
                if version is None or version.source_id != item.source_id:
                    raise ReviewNotFound()
                snapshot = db.get(KnowledgeSnapshot, version.id)
                if (snapshot is None or snapshot.capture_method != "browser_rendered_text"
                        or snapshot.media_type != "text/plain"
                        or snapshot.observed_last_updated is None):
                    raise ReviewConflict("Batch review accepts browser article text only")
                result = approve_version(
                    db, version_id=version.id,
                    expected_digest=item.expected_sha256,
                    actor_subject=principal.subject,
                    reason="Batch browser-source review: " + payload.review_note.strip(),
                )
                results.append(ReviewDecisionResponse(**result.__dict__))
    except ReviewNotFound:
        raise HTTPException(404, "Source version not found") from None
    except ReviewConflict as exc:
        raise HTTPException(409, str(exc)) from None
    return results


@router.get("/sources/{source_id}/history", response_model=list[AuditEventView])
def review_history(
    source_id: str = Path(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=96),
    db: Session = Depends(get_session),
):
    if db.get(KnowledgeSource, source_id) is None:
        raise HTTPException(404, "Source not found")
    rows = db.scalars(
        select(KnowledgeReviewEvent)
        .where(KnowledgeReviewEvent.source_id == source_id)
        .order_by(KnowledgeReviewEvent.occurred_at.desc(), KnowledgeReviewEvent.id.desc())
        .limit(100)
    ).all()
    return [AuditEventView.model_validate(row, from_attributes=True) for row in rows]
