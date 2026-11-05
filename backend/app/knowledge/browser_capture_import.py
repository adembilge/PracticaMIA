"""Offline review-only ingestion of browser-rendered official article text.

The browser text is explicitly identified as *not* the original HTTP HTML.
Nothing is approved, embedded, or released to production by this command.

    python -m app.knowledge.browser_capture_import --directory ./captures
    PRACTICAMIA_KNOWLEDGE_TARGET=staging DATABASE_URL=... \
      python -m app.knowledge.browser_capture_import --directory ./captures --apply

Each JSON file is named <source-id>.json, with fields:
source_id, capture_method, captured_url, page_title, last_updated, article_text.
No full-site accessibility dump, reconstructed HTML or private user content.
"""
import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
from os import environ
from pathlib import Path

from app.database import configure_database
from app.knowledge.browser_capture import validate_browser_metadata
from app.knowledge.catalog import candidate_sources
from app.knowledge.document_extraction import extract_document
from app.knowledge.model import KnowledgeSource
from app.knowledge.snapshots import ingest_snapshot
from app.knowledge.staging_guard import require_staging_intent, require_staging_database


@dataclass(frozen=True)
class Capture:
    source_id: str
    captured_url: str
    page_title: str
    last_updated: str
    body: bytes
    digest: str
    passages: int


def prepare_captures(directory: Path) -> tuple[Capture, ...]:
    if not directory.is_dir() or directory.is_symlink():
        raise ValueError("Captures path must be an existing real directory")
    catalog = {item["id"]: item for item in candidate_sources()}
    results = []
    for path in sorted(directory.iterdir()):
        if path.is_symlink() or not path.is_file() or path.suffix != ".json":
            raise ValueError("Only ordinary JSON capture files are accepted")
        source_id = path.stem
        record = catalog.get(source_id)
        if record is None or record["document_type"] == "official_document":
            raise ValueError("Unknown or non-HTML registered source identifier")
        if path.stat().st_size > 70000:
            raise ValueError("Capture JSON exceeds the permitted size")
        data = json.loads(path.read_text(encoding="utf-8"))
        expected = {
            "source_id", "capture_method", "captured_url",
            "page_title", "last_updated", "article_text",
        }
        if not isinstance(data, dict) or set(data) != expected:
            raise ValueError("Capture must contain exactly the provenance schema")
        if data["source_id"] != source_id:
            raise ValueError("Capture filename and source identifier mismatch")
        if data["capture_method"] != "browser_rendered_text":
            raise ValueError("Only correctly labeled browser captures are accepted")
        source = KnowledgeSource(**record, status="candidate")
        validate_browser_metadata(
            source, observed_url=data["captured_url"],
            observed_title=data["page_title"],
            observed_last_updated=data["last_updated"],
        )
        if not isinstance(data["article_text"], str):
            raise ValueError("Browser capture body must be text")
        body = data["article_text"].encode("utf-8")
        extracted, _ = extract_document(body, "text/plain")
        results.append(Capture(
            source_id=source_id, captured_url=data["captured_url"],
            page_title=data["page_title"], last_updated=data["last_updated"],
            body=body, digest=sha256(body).hexdigest(),
            passages=len(extracted.passages),
        ))
    return tuple(results)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import explicitly labeled browser captures as pending review",
    )
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    captures = prepare_captures(args.directory)
    if not captures:
        parser.error("No browser captures provided")
    print(json.dumps([
        {"source_id": c.source_id, "sha256": c.digest, "passages": c.passages,
         "last_updated": c.last_updated, "capture_method": "browser_rendered_text"}
        for c in captures
    ], indent=2))
    if not args.apply:
        print("Validated only: no database changes or approvals.")
        return

    require_staging_intent()
    db_url = environ.get("DATABASE_URL")
    if not db_url:
        parser.error("DATABASE_URL is required for staging imports")
    engine, factory = configure_database(db_url)
    try:
        with factory.begin() as db:
            require_staging_database(db)
            for capture in captures:
                source = db.get(KnowledgeSource, capture.source_id)
                if source is None:
                    raise ValueError("Source is not registered in knowledge staging")
                outcome = ingest_snapshot(
                    db, source, capture.body, media_type="text/plain",
                    capture_method="browser_rendered_text",
                    observed_url=capture.captured_url,
                    observed_title=capture.page_title,
                    observed_last_updated=capture.last_updated,
                )
                print(outcome.source_id, outcome.revision, outcome.status)
        print("All captures committed as pending_review or unchanged; NO approvals.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
