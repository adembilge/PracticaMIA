"""Transactional, append-only snapshot ingestion with approval invalidation.

The only sanctioned write is pending_review. A changed HTML body invalidates
an older active approval immediately, without mutating the historical content.
No reviewed version or extracted passage is edited in place.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.knowledge.acquisition import MEDIA_TYPES, validate_official_url
from app.knowledge.html_extraction import (
    EXTRACTION_VERSION, MAX_HTML_BYTES, extract_html,
)
from app.knowledge.model import KnowledgeSource, KnowledgeSourceVersion
from app.knowledge.review_model import KnowledgeReviewEvent
from app.knowledge.snapshot_model import KnowledgePassage, KnowledgeSnapshot


@dataclass(frozen=True)
class IngestionResult:
    status: str
    source_id: str
    revision: int
    version_id: str
    sha256: str
    passage_count: int
    previous_approval_invalidated: bool


def ingest_snapshot(
    db: Session, source: KnowledgeSource, body: bytes,
    *, media_type: str = "text/html", retrieved_at: datetime | None = None,
) -> IngestionResult:
    """Call inside an explicit DB transaction. Raises rather than saving partial data."""
    # Lock the source before comparing revisions: approval and ingestion must
    # serialize on the same row in PostgreSQL.
    db.refresh(source, with_for_update=True)
    validate_official_url(source.official_url)
    if media_type not in MEDIA_TYPES:
        raise ValueError("Unsupported snapshot media type")
    if retrieved_at is None:
        retrieved_at = datetime.now(timezone.utc)
    if retrieved_at.tzinfo is None:
        raise ValueError("Retrieval time must be timezone aware")

    # Validate size, UTF-8 and extraction from the exact body being stored.
    if not body or len(body) > MAX_HTML_BYTES:
        raise ValueError("HTML snapshot is empty or exceeds size limit")
    content_hash = sha256(body).hexdigest()
    text = extract_html(body)
    last = db.scalar(
        select(KnowledgeSourceVersion)
        .where(KnowledgeSourceVersion.source_id == source.id)
        .order_by(KnowledgeSourceVersion.revision.desc()).limit(1)
    )
    if last and last.content_sha256 == content_hash:
        return IngestionResult(
            "unchanged", source.id, last.revision, last.id,
            content_hash, len(text.passages), False,
        )

    revision = (last.revision + 1) if last else 1
    new_id = str(uuid4())
    previously_approved = (
        source.status == "approved" or source.active_version_id is not None
    )
    if previously_approved:
        # A content change revokes trust immediately, but preserves history.
        # Keep an auditable record of the previous active source version.
        old_status = source.status
        active = db.get(KnowledgeSourceVersion, source.active_version_id) \
            if source.active_version_id else last
        if active is None or active.source_id != source.id:
            raise ValueError("Approved source has no verifiable active version")
        source.status = "candidate"
        source.active_version_id = None
        db.add(KnowledgeReviewEvent(
            source_id=source.id, version_id=active.id,
            action="source_changed", actor_subject="system:ingestion",
            reason=f"Content change detected; new source SHA-256 {content_hash}",
            content_sha256=active.content_sha256,
            old_source_status=old_status, new_source_status="candidate",
            old_version_status=active.status, new_version_status=active.status,
        ))

    db.add(KnowledgeSourceVersion(
        id=new_id, source_id=source.id, revision=revision,
        content_sha256=content_hash, retrieved_at=retrieved_at,
        status="pending_review", reviewed_at=None, reviewed_by=None,
    ))
    db.add(KnowledgeSnapshot(
        version_id=new_id, fetched_url=source.official_url,
        media_type=media_type, size_bytes=len(body),
        extraction_version=EXTRACTION_VERSION,
        raw_body=body, normalized_text=text.normalized_text,
    ))
    for passage in text.passages:
        db.add(KnowledgePassage(
            id=f"{new_id}:{passage.ordinal:04d}",
            version_id=new_id, ordinal=passage.ordinal,
            section_path=passage.section_path,
            start_offset=passage.start_offset,
            end_offset=passage.end_offset,
            content=passage.content,
            content_sha256=passage.content_sha256,
        ))
    db.flush()
    return IngestionResult(
        "pending_review", source.id, revision, new_id,
        content_hash, len(text.passages), previously_approved,
    )


def verify_snapshot(db: Session, version: KnowledgeSourceVersion) -> bool:
    """Check snapshot byte hash and all provenance offsets before trusting it."""
    snapshot = db.get(KnowledgeSnapshot, version.id)
    if snapshot is None:
        return False
    if (sha256(snapshot.raw_body).hexdigest() != version.content_sha256
            or snapshot.size_bytes != len(snapshot.raw_body)
            or snapshot.extraction_version != EXTRACTION_VERSION):
        return False
    # Provenance includes the extracted text, not just raw HTML bytes.
    # Re-extraction prevents a modified normalized_text/passage pair from
    # passing a superficial offset-only integrity check.
    try:
        extracted = extract_html(snapshot.raw_body)
    except ValueError:
        return False
    if snapshot.normalized_text != extracted.normalized_text:
        return False
    passages = db.scalars(
        select(KnowledgePassage)
        .where(KnowledgePassage.version_id == version.id)
        .order_by(KnowledgePassage.ordinal)
    ).all()
    if not passages or len(passages) != len(extracted.passages):
        return False
    for i, passage in enumerate(passages):
        expected = extracted.passages[i]
        if (passage.ordinal != i
                or passage.section_path != expected.section_path
                or passage.start_offset != expected.start_offset
                or passage.end_offset != expected.end_offset
                or passage.content != expected.content
                or passage.content_sha256 != expected.content_sha256
                or passage.start_offset < 0
                or passage.end_offset > len(snapshot.normalized_text)
                or snapshot.normalized_text[passage.start_offset:passage.end_offset]
                != passage.content
                or sha256(passage.content.encode("utf-8")).hexdigest()
                != passage.content_sha256):
            return False
    return True
