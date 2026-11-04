"""Atomic, reviewer-authorized approval/revocation with immutable audit events.

Operations must run inside one transaction. Callers must obtain the reviewer
identity from an already verified JWT, never from a request body.
"""
from dataclasses import dataclass
from hmac import compare_digest

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.knowledge.model import KnowledgeSource, KnowledgeSourceVersion
from app.knowledge.review_model import KnowledgeReviewEvent
from app.knowledge.snapshot_model import KnowledgeSnapshot
from app.knowledge.snapshots import verify_snapshot


class ReviewConflict(Exception):
    """A source was changed, incomplete, already reviewed, or invalid."""


class ReviewNotFound(Exception):
    """Unknown source version."""


@dataclass(frozen=True)
class ReviewResult:
    source_id: str
    version_id: str
    source_status: str
    version_status: str
    audit_id: str


def _locked_source_version(db: Session, version_id: str):
    """Serialize review with source ingests and other review decisions."""
    initial = db.get(KnowledgeSourceVersion, version_id)
    if initial is None:
        raise ReviewNotFound()
    source = db.scalar(
        select(KnowledgeSource)
        .where(KnowledgeSource.id == initial.source_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if source is None:
        raise ReviewNotFound()
    version = db.scalar(
        select(KnowledgeSourceVersion)
        .where(KnowledgeSourceVersion.id == version_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if version is None or version.source_id != source.id:
        raise ReviewNotFound()
    return source, version


def _validate_digest(version: KnowledgeSourceVersion, expected_digest: str):
    if not compare_digest(version.content_sha256, expected_digest):
        raise ReviewConflict("Source content changed; inspect the latest snapshot")


def _write_event(
    db: Session, *, source: KnowledgeSource, version: KnowledgeSourceVersion,
    action: str, actor_subject: str, reason: str,
    old_source_status: str, old_version_status: str,
) -> KnowledgeReviewEvent:
    event = KnowledgeReviewEvent(
        source_id=source.id, version_id=version.id,
        action=action, actor_subject=actor_subject, reason=reason,
        content_sha256=version.content_sha256,
        old_source_status=old_source_status, new_source_status=source.status,
        old_version_status=old_version_status, new_version_status=version.status,
    )
    db.add(event)
    db.flush()
    return event


def approve_version(
    db: Session, *, version_id: str, expected_digest: str,
    actor_subject: str, reason: str,
) -> ReviewResult:
    source, version = _locked_source_version(db, version_id)
    _validate_digest(version, expected_digest)

    latest_id = db.scalar(
        select(KnowledgeSourceVersion.id)
        .where(KnowledgeSourceVersion.source_id == source.id)
        .order_by(KnowledgeSourceVersion.revision.desc())
        .limit(1)
    )
    if latest_id != version.id:
        raise ReviewConflict("A newer source revision exists; review that revision")
    if (source.status != "candidate" or source.active_version_id is not None
            or version.status != "pending_review" or version.reviewed_at is not None
            or version.reviewed_by is not None):
        raise ReviewConflict("This source revision is not pending review")
    snapshot = db.get(KnowledgeSnapshot, version.id)
    if (snapshot is None or snapshot.fetched_url != source.official_url
            or snapshot.media_type not in ("text/html", "application/xhtml+xml")
            or not verify_snapshot(db, version)):
        raise ReviewConflict("Snapshot integrity or official URL verification failed")

    old_source, old_version = source.status, version.status
    source.status = "approved"
    source.active_version_id = version.id
    version.status = "approved"
    version.reviewed_by = actor_subject
    from datetime import datetime, timezone
    version.reviewed_at = datetime.now(timezone.utc)
    event = _write_event(
        db, source=source, version=version, action="approved",
        actor_subject=actor_subject, reason=reason,
        old_source_status=old_source, old_version_status=old_version,
    )
    return ReviewResult(source.id, version.id, source.status, version.status, event.id)


def revoke_version(
    db: Session, *, version_id: str, expected_digest: str,
    actor_subject: str, reason: str,
) -> ReviewResult:
    source, version = _locked_source_version(db, version_id)
    _validate_digest(version, expected_digest)

    if (source.status != "approved" or source.active_version_id != version.id
            or version.status != "approved"):
        raise ReviewConflict("Only the currently active approved revision can be revoked")
    old_source, old_version = source.status, version.status
    source.status = "revoked"
    source.active_version_id = None
    version.status = "revoked"
    event = _write_event(
        db, source=source, version=version, action="revoked",
        actor_subject=actor_subject, reason=reason,
        old_source_status=old_source, old_version_status=old_version,
    )
    return ReviewResult(source.id, version.id, source.status, version.status, event.id)
