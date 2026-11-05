"""Approval-gated pgvector passage indexing and hybrid retrieval.

Intentionally no public write endpoint, no background ingestion and no
automatic external embedding-provider calls. Model vectors are supplied
explicitly by trusted offline tooling. Only reviewer-approved, latest,
hash-bound passages can be indexed or returned.
"""
from collections import defaultdict
from math import isfinite
import re
from typing import Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.knowledge.search import (
    EvidencePassage, normalize_query, resolve_approved_passage,
    search_approved_passages,
)

EMBEDDING_DIMENSIONS = 1536
MAX_VECTOR_CANDIDATES = 100
RRF_K = 60
MODEL_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,95}$")


def _postgres_only(db: Session) -> None:
    if db.get_bind().dialect.name != "postgresql":
        raise RuntimeError("Vector retrieval requires migrated PostgreSQL with pgvector")


def _encode_vector(vector: Sequence[float]) -> str:
    if len(vector) != EMBEDDING_DIMENSIONS:
        raise ValueError("Embedding must contain exactly 1536 dimensions")
    values = [float(value) for value in vector]
    if any(not isfinite(value) for value in values) or not any(values):
        raise ValueError("Embedding must be finite and nonzero")
    return "[" + ",".join(format(value, ".9g") for value in values) + "]"


def _model_id(model_id: str) -> str:
    if not MODEL_PATTERN.fullmatch(model_id):
        raise ValueError("A valid embedding model ID is required")
    return model_id


def index_approved_passage_vector(
    db: Session, *, citation_id: str, jurisdiction: str,
    procedure_id: str, language: str, model_id: str,
    embedding: Sequence[float],
) -> bool:
    """Insert or replace a vector *only* for a presently trusted passage.

    Caller controls the provider and any transmission of approved public text;
    production keys are not needed to test this module. Use inside a transaction.
    """
    _postgres_only(db)
    encoded = _encode_vector(embedding)
    model_id = _model_id(model_id)
    evidence = resolve_approved_passage(
        db, citation_id=citation_id, jurisdiction=jurisdiction,
        procedure_id=procedure_id, language=language,
    )
    if evidence is None:
        return False
    db.execute(text("""
        INSERT INTO knowledge_passage_embeddings
            (passage_id, model_id, version_id, passage_sha256, embedding)
        VALUES
            (:passage_id, :model_id, :version_id, :passage_sha256,
             CAST(:embedding AS vector(1536)))
        ON CONFLICT (passage_id, model_id)
        DO UPDATE SET version_id = EXCLUDED.version_id,
            passage_sha256 = EXCLUDED.passage_sha256,
            embedding = EXCLUDED.embedding
    """), {
        "passage_id": evidence.passage_id, "model_id": model_id,
        "version_id": evidence.source_version_id,
        "passage_sha256": evidence.passage_sha256, "embedding": encoded,
    })
    return True


def search_approved_semantic(
    db: Session, *, query_embedding: Sequence[float], model_id: str,
    jurisdiction: str, procedure_id: str, language: str, limit: int = 5,
) -> list[EvidencePassage]:
    """Rank with cosine distance, then re-check every hash-bound citation.

    SQL first limits scope and active metadata; Python verifies the *latest*
    approval audit event, original bytes, passage hash and extraction offsets.
    No raw candidate or stale document is disclosed.
    """
    _postgres_only(db)
    if not 1 <= limit <= 10:
        raise ValueError("Limit must be between 1 and 10")
    encoded = _encode_vector(query_embedding)
    model_id = _model_id(model_id)
    rows = db.execute(text("""
        SELECT p.id AS passage_id
        FROM knowledge_passage_embeddings AS e
        JOIN knowledge_source_passages AS p
            ON p.id = e.passage_id AND p.version_id = e.version_id
        JOIN knowledge_source_versions AS v ON v.id = e.version_id
        JOIN knowledge_sources AS s ON s.id = v.source_id
        WHERE e.model_id = :model_id
          AND e.passage_sha256 = p.content_sha256
          AND s.status = 'approved'
          AND s.active_version_id = v.id
          AND v.status = 'approved'
          AND v.reviewed_at IS NOT NULL
          AND v.reviewed_by IS NOT NULL
          AND s.jurisdiction = :jurisdiction
          AND s.procedure_id = :procedure_id
          AND s.language = :language
        ORDER BY e.embedding <=> CAST(:embedding AS vector(1536)), p.id
        LIMIT :candidate_limit
    """), {
        "model_id": model_id, "jurisdiction": jurisdiction,
        "procedure_id": procedure_id, "language": language,
        "embedding": encoded, "candidate_limit": MAX_VECTOR_CANDIDATES,
    }).all()
    result: list[EvidencePassage] = []
    for row in rows:
        passage = resolve_approved_passage(
            db, citation_id=row.passage_id, jurisdiction=jurisdiction,
            procedure_id=procedure_id, language=language,
        )
        if passage is not None:
            result.append(passage)
            if len(result) == limit:
                break
    return result


def fuse_ranked_passages(
    lexical: Sequence[EvidencePassage],
    semantic: Sequence[EvidencePassage],
    *, limit: int = 5,
) -> list[EvidencePassage]:
    """Stable reciprocal-rank fusion. Never invents a passage or citation."""
    if not 1 <= limit <= 10:
        raise ValueError("Limit must be between 1 and 10")
    scores: dict[str, float] = defaultdict(float)
    unique: dict[str, EvidencePassage] = {}
    for ranking in (lexical, semantic):
        for rank, passage in enumerate(ranking, start=1):
            # Avoid boosting duplicate citation IDs within a single modality.
            if passage.citation_id in {p.citation_id for p in ranking[:rank-1]}:
                continue
            unique[passage.citation_id] = passage
            scores[passage.citation_id] += 1 / (RRF_K + rank)
    ranked = sorted(unique, key=lambda cid: (-scores[cid], cid))
    return [unique[citation] for citation in ranked[:limit]]


def search_approved_hybrid(
    db: Session, *, query: str, jurisdiction: str,
    procedure_id: str, language: str, limit: int = 5,
    query_embedding: Sequence[float] | None = None,
    model_id: str | None = None,
) -> list[EvidencePassage]:
    """Hybrid approved-only search, or lexical-only without an embedding.

    Must be invoked with a validated scope from trusted case state,
    not arbitrary model-generated jurisdiction or procedure values.
    """
    normalize_query(query)
    if (query_embedding is None) != (model_id is None):
        raise ValueError("Semantic query and model ID must be provided together")
    lexical = search_approved_passages(
        db, query=query, jurisdiction=jurisdiction, procedure_id=procedure_id,
        language=language, limit=10,
    )
    semantic = (
        search_approved_semantic(
            db, query_embedding=query_embedding, model_id=model_id,
            jurisdiction=jurisdiction, procedure_id=procedure_id,
            language=language, limit=10,
        ) if query_embedding is not None else []
    )
    return fuse_ranked_passages(lexical, semantic, limit=limit)
