"""Approved-only lexical evidence search. Never derives legal rules or eligibility.

Production PostgreSQL uses a GIN-indexed full-text predicate. SQLite is a
deterministic, bounded fallback for isolated unit tests, not production search.
All candidates are filtered by active version, procedure, jurisdiction, and
language before ranking, then independently checked against raw snapshots.
"""
from dataclasses import dataclass
from datetime import datetime
import re
from sqlalchemy import func, literal_column, select
from sqlalchemy.orm import Session

from app.knowledge.model import KnowledgeSource, KnowledgeSourceVersion
from app.knowledge.review_model import KnowledgeReviewEvent
from app.knowledge.snapshot_model import KnowledgePassage, KnowledgeSnapshot
from app.knowledge.snapshots import verify_snapshot

MAX_CANDIDATES = 200
MAX_QUERY_TERMS = 12
_TERM_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)


@dataclass(frozen=True)
class EvidencePassage:
    citation_id: str
    passage_id: str
    source_id: str
    source_version_id: str
    source_revision: int
    institution: str
    title: str
    official_url: str
    jurisdiction: str
    procedure_id: str
    language: str
    section_path: str
    content: str
    passage_sha256: str
    source_sha256: str
    reviewed_at: datetime
    retrieved_at: datetime


def normalize_query(raw: str) -> tuple[str, tuple[str, ...]]:
    """Eliminate search syntax rather than execute an LLM-supplied query language."""
    terms = tuple(_TERM_PATTERN.findall(raw.casefold()))
    if not terms or len(terms) > MAX_QUERY_TERMS or len(raw) > 180:
        raise ValueError("Search must contain 1-12 words and at most 180 characters")
    return " ".join(terms), terms


def _approved_scope(
    jurisdiction: str, procedure_id: str, language: str,
):
    """Metadata gates are enforced in SQL, before text matching or ranking."""
    return (
        select(KnowledgeSource, KnowledgeSourceVersion, KnowledgePassage)
        .join(KnowledgeSourceVersion,
              KnowledgeSourceVersion.source_id == KnowledgeSource.id)
        .join(KnowledgePassage,
              KnowledgePassage.version_id == KnowledgeSourceVersion.id)
        .where(KnowledgeSource.status == "approved")
        .where(KnowledgeSource.active_version_id == KnowledgeSourceVersion.id)
        .where(KnowledgeSourceVersion.status == "approved")
        .where(KnowledgeSourceVersion.reviewed_at.is_not(None))
        .where(KnowledgeSourceVersion.reviewed_by.is_not(None))
        .where(KnowledgeSource.jurisdiction == jurisdiction)
        .where(KnowledgeSource.procedure_id == procedure_id)
        .where(KnowledgeSource.language == language)
    )


def trusted_active_version(
    db: Session, source: KnowledgeSource,
    version: KnowledgeSourceVersion, checked: dict[str, bool],
) -> bool:
    cached = checked.get(version.id)
    if cached is not None:
        return cached

    correct_hash = bool(re.fullmatch(r"[0-9a-f]{64}", version.content_sha256))
    latest_revision = db.scalar(
        select(func.max(KnowledgeSourceVersion.revision))
        .where(KnowledgeSourceVersion.source_id == source.id)
    )
    # A status field alone does not establish that a human reviewer
    # approved this version. The *latest* event must confirm approval,
    # excluding a version subsequently revoked or invalidated.
    last_event = db.scalar(
        select(KnowledgeReviewEvent)
        .where(KnowledgeReviewEvent.source_id == source.id)
        .where(KnowledgeReviewEvent.version_id == version.id)
        .order_by(KnowledgeReviewEvent.occurred_at.desc(),
                  KnowledgeReviewEvent.id.desc())
        .limit(1)
    )
    approved_event = bool(
        last_event is not None
        and last_event.action == "approved"
        and last_event.actor_subject == version.reviewed_by
        and last_event.content_sha256 == version.content_sha256
        and last_event.new_source_status == "approved"
        and last_event.new_version_status == "approved"
    )
    snapshot = db.get(KnowledgeSnapshot, version.id)
    accepted = bool(
        correct_hash
        and latest_revision == version.revision
        and approved_event
        and snapshot is not None
        and snapshot.fetched_url == source.official_url
        and snapshot.media_type in ("text/html", "application/xhtml+xml")
        and verify_snapshot(db, version)
    )
    checked[version.id] = accepted
    return accepted


def _evidence(
    source: KnowledgeSource, version: KnowledgeSourceVersion,
    passage: KnowledgePassage,
) -> EvidencePassage:
    return EvidencePassage(
        citation_id=passage.id, passage_id=passage.id,
        source_id=source.id, source_version_id=version.id,
        source_revision=version.revision,
        institution=source.institution, title=source.title,
        official_url=source.official_url,
        jurisdiction=source.jurisdiction,
        procedure_id=source.procedure_id, language=source.language,
        section_path=passage.section_path, content=passage.content,
        passage_sha256=passage.content_sha256,
        source_sha256=version.content_sha256,
        reviewed_at=version.reviewed_at, retrieved_at=version.retrieved_at,
    )


def search_approved_passages(
    db: Session, *, query: str, jurisdiction: str,
    procedure_id: str, language: str, limit: int = 5,
) -> list[EvidencePassage]:
    """Return at most ten exact-citation passages; no unreviewed text ever leaks."""
    if not 1 <= limit <= 10:
        raise ValueError("Limit must be between 1 and 10")
    cleaned, terms = normalize_query(query)
    statement = _approved_scope(jurisdiction, procedure_id, language)
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        # This expression exactly matches the GIN expression index in 0006.
        configuration = literal_column("'simple'::regconfig")
        vector = func.to_tsvector(configuration, KnowledgePassage.content)
        query_vector = func.plainto_tsquery(configuration, cleaned)
        rank = func.ts_rank_cd(vector, query_vector)
        statement = (
            statement
            .where(vector.bool_op("@@")(query_vector))
            .order_by(rank.desc(), KnowledgePassage.id.asc())
            .limit(MAX_CANDIDATES)
        )
        candidates = [
            (source, version, passage, float(score))
            for source, version, passage, score in db.execute(
                statement.add_columns(rank.label("search_score"))
            ).all()
        ]
    elif dialect == "sqlite":
        # Used only by isolated tests; real deployments require PostgreSQL.
        rows = db.execute(statement.limit(MAX_CANDIDATES)).all()
        candidates = []
        for source, version, passage in rows:
            words = _TERM_PATTERN.findall(passage.content.casefold())
            if all(term in words for term in terms):
                score = sum(words.count(term) for term in terms) / (1 + len(words))
                candidates.append((source, version, passage, score))
        candidates.sort(key=lambda item: (-item[3], item[2].id))
    else:
        raise RuntimeError("Approved search requires PostgreSQL")

    output: list[EvidencePassage] = []
    checked: dict[str, bool] = {}
    for source, version, passage, _ in candidates:
        if not trusted_active_version(db, source, version, checked):
            continue
        output.append(_evidence(source, version, passage))
        if len(output) == limit:
            break
    return output


def resolve_approved_passage(
    db: Session, *, citation_id: str, jurisdiction: str,
    procedure_id: str, language: str,
) -> EvidencePassage | None:
    """Resolve one citation only while its exact source version remains trusted."""
    rows = db.execute(
        _approved_scope(jurisdiction, procedure_id, language)
        .where(KnowledgePassage.id == citation_id)
        .limit(1)
    ).all()
    if not rows:
        return None
    source, version, passage = rows[0]
    return _evidence(source, version, passage) if trusted_active_version(
        db, source, version, {}
    ) else None
