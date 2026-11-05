"""Reviewable, offline intake of genuine original municipal HTML/PDF files.

Commands (run from backend/):
  python -m app.knowledge.batch_import --queue
  python -m app.knowledge.batch_import --directory ./official-originals
  python -m app.knowledge.batch_import --directory ./official-originals --apply

The default is a read-only JSON acquisition queue or dry-run. The --apply
operation is restricted to a migrated PostgreSQL knowledge staging database;
it cannot approve anything. Never treat search excerpts, reconstructed HTML,
screenshots or converted PDF text as genuine source originals.
"""
import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
from os import environ
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.database import configure_database
from app.knowledge.catalog import candidate_sources
from app.knowledge.document_extraction import extract_document
from app.knowledge.ingest_source import _read_original_file
from app.knowledge.model import KnowledgeSource, KnowledgeSourceVersion
from app.knowledge.snapshots import ingest_snapshot


@dataclass(frozen=True)
class PreparedOriginal:
    source_id: str
    url: str
    body: bytes
    media_type: str
    sha256: str
    passage_count: int


def prepare_directory(
    directory: Path, candidates: list[dict[str, str]] | None = None,
) -> tuple[PreparedOriginal, ...]:
    """Validate every original before opening a DB transaction.

    Only exact curated source IDs are accepted as filenames. Symlinks,
    unexpected files, duplicates, unsupported types, invalid extraction and
    excessive content all fail closed rather than being silently skipped.
    """
    entries = candidates if candidates is not None else candidate_sources()
    catalog = {source["id"]: source for source in entries}
    if not directory.is_dir() or directory.is_symlink():
        raise ValueError("Originals directory must be an existing real directory")
    originals: list[PreparedOriginal] = []
    seen: set[str] = set()
    for file in sorted(directory.iterdir()):
        if file.is_symlink() or not file.is_file():
            raise ValueError(f"Unexpected or linked directory entry: {file.name}")
        suffix = file.suffix.lower()
        if suffix not in {".html", ".htm", ".pdf"}:
            raise ValueError(f"Unsupported original filename: {file.name}")
        source_id = file.stem
        source = catalog.get(source_id)
        if source is None:
            raise ValueError(f"File not mapped to a registered source ID: {file.name}")
        if source_id in seen:
            raise ValueError(f"Duplicate original for source: {source_id}")
        seen.add(source_id)
        expected_pdf = source["document_type"] == "official_document"
        if expected_pdf != (suffix == ".pdf"):
            raise ValueError(f"Original file type differs from registry: {source_id}")
        body, media_type = _read_original_file(file)
        extracted, _ = extract_document(body, media_type)
        originals.append(PreparedOriginal(
            source_id=source_id, url=source["official_url"], body=body,
            media_type=media_type, sha256=sha256(body).hexdigest(),
            passage_count=len(extracted.passages),
        ))
    return tuple(originals)


def queue_records(
    candidates: list[dict[str, str]], db: Session | None = None,
) -> list[dict[str, str | int | None]]:
    """A metadata-only download queue; does not retrieve or approve sources."""
    latest: dict[str, KnowledgeSourceVersion] = {}
    if db is not None:
        versions = db.scalars(
            select(KnowledgeSourceVersion)
            .order_by(KnowledgeSourceVersion.source_id,
                      KnowledgeSourceVersion.revision.desc())
        ).all()
        for version in versions:
            latest.setdefault(version.source_id, version)
    queue: list[dict[str, str | int | None]] = []
    for src in candidates:
        version = latest.get(src["id"])
        state = version.status if version else "not_imported"
        queue.append({
            "source_id": src["id"],
            "title": src["title"],
            "official_url": src["official_url"],
            "expected_extension": ".pdf" if src["document_type"] == "official_document" else ".html",
            "stored_version_status": state,
            "stored_revision": version.revision if version else None,
            "action": (
                "verify_original_and_review" if state == "pending_review"
                else "monitor_approved_source" if state == "approved"
                else "download_original_and_review"
            ),
        })
    return queue


def ingest_prepared(
    db: Session, originals: tuple[PreparedOriginal, ...],
) -> list[dict[str, str | int | bool]]:
    """Ingest prevalidated originals inside a caller-owned DB transaction.

    If any registered source or URL has changed, the entire transaction
    raises and must roll back. Never alters source approval to approved.
    """
    if not originals:
        raise ValueError("No original files supplied")
    results: list[dict[str, str | int | bool]] = []
    for original in originals:
        source = db.get(KnowledgeSource, original.source_id)
        if source is None or source.official_url != original.url:
            raise ValueError(f"Registered source missing or URL changed: {original.source_id}")
        result = ingest_snapshot(
            db, source, original.body, media_type=original.media_type,
        )
        results.append({
            "source_id": result.source_id,
            "version_id": result.version_id,
            "revision": result.revision,
            "status": result.status,
            "sha256": result.sha256,
            "passage_count": result.passage_count,
            "previous_approval_invalidated": result.previous_approval_invalidated,
        })
    return results


def require_staging_database(db: Session) -> None:
    """Conservative hard gate: production is not on this migration."""
    if db.get_bind().dialect.name != "postgresql":
        raise ValueError("Manual batch writes require PostgreSQL staging")
    revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    if revision != "20261105_0008":
        raise ValueError(
            "Batch importer requires knowledge staging at migration 20261105_0008"
        )


def _summary(original: PreparedOriginal) -> dict[str, str | int]:
    return {
        "source_id": original.source_id,
        "media_type": original.media_type,
        "size_bytes": len(original.body),
        "sha256": original.sha256,
        "passage_count": original.passage_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Queue and safely import exact original official documents",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--queue", action="store_true",
                      help="List registered sources with DB statuses if DATABASE_URL is set")
    mode.add_argument("--directory", type=Path,
                      help="Prepare files named <source-id>.html or <source-id>.pdf")
    parser.add_argument("--apply", action="store_true",
                        help="Explicitly save as pending review in migrated staging only")
    args = parser.parse_args()

    if args.queue and args.apply:
        parser.error("A queue listing is read-only")
    candidates = candidate_sources()
    db_url = environ.get("DATABASE_URL", "")
    if args.queue:
        if not db_url:
            print(json.dumps(queue_records(candidates), indent=2, ensure_ascii=False))
            return
        engine, factory = configure_database(db_url)
        try:
            with factory() as db:
                print(json.dumps(queue_records(candidates, db), indent=2,
                                 ensure_ascii=False))
        finally:
            engine.dispose()
        return

    prepared = prepare_directory(args.directory, candidates)
    if not prepared:
        parser.error("Directory has no original source files")
    print(json.dumps({
        "mode": "validated_originals",
        "count": len(prepared),
        "documents": [_summary(item) for item in prepared],
    }, indent=2, ensure_ascii=False))
    if not args.apply:
        print("Dry run only: no database changes and no approvals.")
        return

    if not db_url:
        parser.error("DATABASE_URL is required for --apply")
    if environ.get("PRACTICAMIA_KNOWLEDGE_TARGET") != "staging":
        parser.error(
            "Set PRACTICAMIA_KNOWLEDGE_TARGET=staging explicitly for --apply"
        )
    if environ.get("VERCEL_ENV") == "production":
        parser.error("Batch imports are prohibited in Vercel production")
    engine, factory = configure_database(db_url)
    try:
        with factory.begin() as db:
            require_staging_database(db)
            results = ingest_prepared(db, prepared)
        print(json.dumps({
            "mode": "pending_review_import_complete", "results": results,
        }, indent=2, ensure_ascii=False))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
