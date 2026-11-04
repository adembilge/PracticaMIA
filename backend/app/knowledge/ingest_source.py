"""Explicit one-source HTML snapshot ingest; never scheduled or exposed via API.

Dry-run:
  python -m app.knowledge.ingest_source --source-id milano-residence-change --file page.html

Apply to a *migrated, reviewed target database*:
  python -m app.knowledge.ingest_source --source-id milano-residence-change --file page.html --apply

Live acquisition is explicitly opted into with --fetch (no crawler, redirects,
or retries). Before using it, check site terms and access permissions.
"""
import argparse
from hashlib import sha256
from os import environ
from pathlib import Path

from app.database import configure_database
from app.knowledge.acquisition import fetch_official_html
from app.knowledge.catalog import candidate_sources
from app.knowledge.html_extraction import MAX_HTML_BYTES, extract_html
from app.knowledge.model import KnowledgeSource
from app.knowledge.snapshots import ingest_snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest one untrusted official HTML snapshot")
    parser.add_argument("--source-id", required=True)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--file", type=Path, help="UTF-8 HTML file for manual import")
    input_group.add_argument("--fetch", action="store_true",
                             help="Fetch exact allowlisted official URL once")
    parser.add_argument("--apply", action="store_true",
                        help="Write a pending-review snapshot to DATABASE_URL")
    args = parser.parse_args()

    catalog = {item["id"]: item for item in candidate_sources()}
    candidate = catalog.get(args.source_id)
    if not candidate:
        parser.error("Unknown curated candidate source ID")

    if args.file is not None:
        with args.file.open("rb") as fp:
            body = fp.read(MAX_HTML_BYTES + 1)
        media_type = "text/html"
    else:
        body, media_type = fetch_official_html(candidate["official_url"])

    extracted = extract_html(body)
    digest = sha256(body).hexdigest()
    print(f"Source {args.source_id}; SHA-256 {digest}; passages {len(extracted.passages)}")
    if not args.apply:
        print("Dry-run complete: no database changes and no approval.")
        return

    db_url = environ.get("DATABASE_URL")
    if not db_url:
        parser.error("DATABASE_URL is required with --apply")
    engine, factory = configure_database(db_url)
    try:
        with factory.begin() as db:
            source = db.get(KnowledgeSource, args.source_id)
            if source is None:
                raise ValueError("Register the candidate source first")
            if source.official_url != candidate["official_url"]:
                raise ValueError("Registered source URL differs from reviewed catalog")
            result = ingest_snapshot(
                db, source, body, media_type=media_type,
            )
        print(f"Revision {result.revision}: {result.status}; "
              f"previous approval invalidated={result.previous_approval_invalidated}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
