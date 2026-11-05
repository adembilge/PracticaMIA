"""Explicit single-source HTML/PDF ingestion, without autoapproval.

Dry-run from backend/:
  python -m app.knowledge.ingest_source --source-id milano-residence-change --file original.html

Only on an isolated migrated staging database (explicit staging marker required), after inspecting the original:
  python -m app.knowledge.ingest_source --source-id <registered-id> --file original.pdf --apply

Live acquisition via --fetch is opt-in and refuses HTTP 403 and redirects.
Do not use search snippets, reconstructed text or unauthorized downloads.
"""
import argparse
from hashlib import sha256
from os import environ
from pathlib import Path

from app.database import configure_database
from app.knowledge.acquisition import fetch_official_document
from app.knowledge.catalog import candidate_sources
from app.knowledge.document_extraction import (
    MEDIA_LIMITS, extract_document,
)
from app.knowledge.model import KnowledgeSource
from app.knowledge.snapshots import ingest_snapshot
from app.knowledge.staging_guard import require_staging_database, require_staging_intent


def _read_original_file(path: Path) -> tuple[bytes, str]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        media_type = "application/pdf"
    elif suffix in (".html", ".htm"):
        media_type = "text/html"
    else:
        raise ValueError("Manual source file must end in .pdf, .html or .htm")
    with path.open("rb") as stream:
        body = stream.read(MEDIA_LIMITS[media_type] + 1)
    return body, media_type


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest one original official HTML/PDF snapshot as pending review",
    )
    parser.add_argument("--source-id", required=True)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--file", type=Path, help="Original HTML/PDF file; never a reconstructed summary")
    input_group.add_argument("--fetch", action="store_true",
                             help="Request exact allowlisted official URL once, refusing redirects")
    parser.add_argument("--apply", action="store_true",
                        help="Write an unapproved version only to DATABASE_URL")
    args = parser.parse_args()

    catalog = {item["id"]: item for item in candidate_sources()}
    candidate = catalog.get(args.source_id)
    if not candidate:
        parser.error("Unknown registered official source ID")

    if args.file:
        body, media_type = _read_original_file(args.file)
    else:
        body, media_type = fetch_official_document(candidate["official_url"])

    expected_pdf = candidate["document_type"] == "official_document"
    if expected_pdf != (media_type == "application/pdf"):
        raise ValueError("Original media type does not match the curated source's document type")
    extracted, extraction_version = extract_document(body, media_type)
    digest = sha256(body).hexdigest()
    print(
        f"Source {args.source_id}; media {media_type}; extractor {extraction_version}; "
        f"SHA-256 {digest}; passages {len(extracted.passages)}"
    )
    if not args.apply:
        print("Dry-run complete: no database changes and no approval.")
        return

    db_url = environ.get("DATABASE_URL")
    if not db_url:
        parser.error("DATABASE_URL is required with --apply")
    require_staging_intent()
    engine, factory = configure_database(db_url)
    try:
        with factory.begin() as db:
            require_staging_database(db)
            source = db.get(KnowledgeSource, args.source_id)
            if source is None:
                raise ValueError("Register the candidate source before ingestion")
            if source.official_url != candidate["official_url"]:
                raise ValueError("Database source URL differs from curated original")
            result = ingest_snapshot(db, source, body, media_type=media_type)
        print(f"Revision {result.revision}: {result.status}; "
              f"previous approval invalidated={result.previous_approval_invalidated}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
