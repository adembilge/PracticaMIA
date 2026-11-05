"""Explicit, approval-gated 1536-dimensional pgvector indexing.

Dry-run by default; never sends any text to an external provider unless the
operator *separately* enables --apply and --confirm-public-source-transfer.
All embeddings are generated from individually approved and hash-verified
municipal passages only. No user cases, private case data, unreviewed PDFs or
pending browser captures are ever sent to the provider.

From backend/:
  DATABASE_URL=... PRACTICAMIA_KNOWLEDGE_TARGET=staging \
    python -m app.knowledge.approved_embedding_index

  DATABASE_URL=... PRACTICAMIA_KNOWLEDGE_TARGET=staging OPENAI_API_KEY=... \
    python -m app.knowledge.approved_embedding_index \
      --apply --confirm-public-source-transfer
"""
import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
from math import isfinite
from os import environ
from typing import Protocol, Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import configure_database
from app.knowledge.search import _approved_scope, resolve_approved_passage
from app.knowledge.snapshot_model import KnowledgePassage
from app.knowledge.staging_guard import require_staging_database, require_staging_intent
from app.knowledge.vector_search import (
    EMBEDDING_DIMENSIONS, index_approved_passage_vector,
)

SCOPE = {
    "jurisdiction": "IT-MI-MILANO",
    "procedure_id": "milan_residence_change",
    "language": "it",
}
MODEL_ID = "text-embedding-3-small"
MAX_PASSAGES = 100


@dataclass(frozen=True)
class EmbeddingTask:
    citation_id: str
    source_id: str
    version_id: str
    passage_sha256: str
    content: str


class DocumentEmbedder(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...


def plan_approved_unindexed(
    db: Session, *, model_id: str = MODEL_ID,
    max_passages: int = MAX_PASSAGES,
) -> list[EmbeddingTask]:
    """Select only current human-approved passages with immutable hashes."""
    if db.get_bind().dialect.name != "postgresql":
        raise ValueError("Embedding planning requires pgvector PostgreSQL")
    if model_id != MODEL_ID:
        raise ValueError("Only the evaluated 1536-dimensional model is permitted")
    if not 1 <= max_passages <= MAX_PASSAGES:
        raise ValueError("Passage budget must be between 1 and 100")
    # Filter approved metadata first, then independently validate source bytes,
    # exact passage spans and the latest immutable approval audit event.
    rows = db.execute(
        _approved_scope(**SCOPE)
        .order_by(KnowledgePassage.id.asc())
        .limit(MAX_PASSAGES + 1)
    ).all()
    if len(rows) > MAX_PASSAGES:
        raise ValueError("Over 100 approved passages; partition the corpus first")
    existing = {
        row.passage_id: row.passage_sha256
        for row in db.execute(text("""
            SELECT passage_id, passage_sha256
              FROM knowledge_passage_embeddings
             WHERE model_id = :model_id
        """), {"model_id": model_id}).all()
    }
    tasks: list[EmbeddingTask] = []
    for _source, _version, passage in rows:
        evidence = resolve_approved_passage(
            db, citation_id=passage.id, **SCOPE,
        )
        if evidence is None:
            continue
        if existing.get(evidence.citation_id) == evidence.passage_sha256:
            continue
        if not evidence.content or sha256(
            evidence.content.encode("utf-8")
        ).hexdigest() != evidence.passage_sha256:
            raise ValueError("Approved passage hash changed during indexing plan")
        tasks.append(EmbeddingTask(
            citation_id=evidence.citation_id, source_id=evidence.source_id,
            version_id=evidence.source_version_id,
            passage_sha256=evidence.passage_sha256, content=evidence.content,
        ))
    if len(tasks) > max_passages:
        raise ValueError("Indexing budget is too small for approved unindexed corpus")
    return tasks


def prepare_vectors(
    embedder: DocumentEmbedder, tasks: Sequence[EmbeddingTask],
) -> list[list[float]]:
    """Call the selected provider at most once for an explicitly bounded batch.

    This function never receives user case records or auth metadata. The
    operator must complete a privacy/cost review before invoking the CLI.
    """
    if not tasks:
        return []
    vectors = embedder.embed_documents([task.content for task in tasks])
    if len(vectors) != len(tasks):
        raise ValueError("Embedding provider returned an unexpected number of vectors")
    for vector in vectors:
        if (len(vector) != EMBEDDING_DIMENSIONS
                or not all(isfinite(float(value)) for value in vector)
                or not any(float(value) != 0.0 for value in vector)):
            raise ValueError("Embedding provider returned an invalid vector")
    return vectors


def save_vectors(
    db: Session, tasks: Sequence[EmbeddingTask],
    vectors: Sequence[Sequence[float]], *,
    model_id: str = MODEL_ID,
) -> int:
    """All-or-nothing write within a caller-owned transaction.

    Revalidate each citation and its digest *after* the provider call, so a
    source revoked or updated during the call cannot be indexed as trusted.
    """
    if len(tasks) != len(vectors):
        raise ValueError("Vector count and task count must match")
    for task, vector in zip(tasks, vectors, strict=True):
        current = resolve_approved_passage(
            db, citation_id=task.citation_id, **SCOPE,
        )
        if (current is None or current.source_version_id != task.version_id
                or current.passage_sha256 != task.passage_sha256
                or current.content != task.content):
            raise ValueError("Source approval or exact passage changed during indexing")
        if not index_approved_passage_vector(
            db, citation_id=task.citation_id, embedding=vector,
            model_id=model_id, **SCOPE,
        ):
            raise ValueError("Unapproved passage cannot be indexed")
    return len(tasks)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dry-run or explicitly index reviewed public sources",
    )
    parser.add_argument("--apply", action="store_true",
                        help="Explicitly persist embeddings of approved passages")
    parser.add_argument("--confirm-public-source-transfer", action="store_true",
                        help="Confirm provider transfer of reviewed public text")
    parser.add_argument("--max-passages", type=int, default=MAX_PASSAGES)
    args = parser.parse_args()
    if args.confirm_public_source_transfer and not args.apply:
        parser.error("Provider-transfer confirmation is meaningful only with --apply")
    require_staging_intent()
    url = environ.get("DATABASE_URL", "")
    if not url:
        parser.error("Set DATABASE_URL to the isolated staging branch")
    if args.apply and not args.confirm_public_source_transfer:
        parser.error("--apply requires --confirm-public-source-transfer")
    if args.apply and not environ.get("OPENAI_API_KEY", ""):
        parser.error("OPENAI_API_KEY is required for explicit provider calls")

    engine, factory = configure_database(url)
    try:
        with factory() as db:
            require_staging_database(db)
            tasks = plan_approved_unindexed(db, max_passages=args.max_passages)
        print(json.dumps({
            "model_id": MODEL_ID, "dimensions": EMBEDDING_DIMENSIONS,
            "pending_approved_passages": len(tasks),
            "status": "dry_run_no_external_calls" if not args.apply else
                      "reviewed_public_text_only",
            "passages": [
                {"citation_id": t.citation_id, "source_id": t.source_id,
                 "passage_sha256": t.passage_sha256}
                for t in tasks
            ],
        }, indent=2))
        if not args.apply:
            print("Nothing written; no embedding provider contacted.")
            return
        if not tasks:
            print("No approved, unindexed passages; no provider call needed.")
            return
        # LangChain provider is imported only in the explicit --apply path.
        from langchain_openai import OpenAIEmbeddings
        provider = OpenAIEmbeddings(
            model=MODEL_ID, dimensions=EMBEDDING_DIMENSIONS,
            api_key=environ["OPENAI_API_KEY"],
            max_retries=0, request_timeout=20,
        )
        # No text is logged. Provider failure cannot create partial DB rows.
        vectors = prepare_vectors(provider, tasks)
        with factory.begin() as db:
            require_staging_database(db)
            indexed = save_vectors(db, tasks, vectors)
        print(f"Indexed {indexed} approved public passages in staging.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
