"""Import the pinned Phase 4 originals for local or isolated Preview review."""

import argparse
from dataclasses import asdict
from datetime import timezone
import json
from os import environ
from pathlib import Path

from sqlalchemy import URL, create_engine, inspect, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import Base
from app.knowledge.batch_import import PreparedOriginal, prepare_directory
from app.knowledge.model import KnowledgeSource, KnowledgeSourceVersion
from app.knowledge.pilot_sources import (
    PILOT_CLAIM_PASSAGES, PILOT_REVIEW_APPLICATION_ID, PILOT_SOURCES, POSTAL_APPOINTMENT_SOURCE_ID,
)
from app.knowledge.review_model import KnowledgeReviewEvent
from app.knowledge.snapshot_model import KnowledgePassage, KnowledgeSnapshot
from app.knowledge.snapshots import ingest_snapshot, verify_snapshot
from app.knowledge.staging_guard import require_pilot_preview_database, require_pilot_preview_target


TABLES = tuple(model.__table__ for model in (
    KnowledgeSource, KnowledgeSourceVersion, KnowledgeSnapshot, KnowledgePassage, KnowledgeReviewEvent,
))


def _check_database(connection) -> None:
    application_id = connection.exec_driver_sql("PRAGMA application_id").scalar_one()
    tables = set(inspect(connection).get_table_names())
    if application_id == 0 and not tables:
        connection.exec_driver_sql(f"PRAGMA application_id = {PILOT_REVIEW_APPLICATION_ID}")
        Base.metadata.create_all(connection, tables=TABLES)
    elif application_id != PILOT_REVIEW_APPLICATION_ID or tables != {table.name for table in TABLES}:
        raise ValueError("Choose a new file or an existing Phase 4 review catalogue")


def _prepare_originals(originals_dir: Path, *, include_postal: bool = False) -> tuple[PreparedOriginal, ...]:
    records = {key: source.registry_fields(key) for key, source in PILOT_SOURCES.items()}
    originals = prepare_directory(
        originals_dir, list(records.values()),
        extraction_versions={key: source.extraction_version for key, source in PILOT_SOURCES.items()},
    )
    source_ids = {item.source_id for item in originals}
    if source_ids - {POSTAL_APPOINTMENT_SOURCE_ID} != records.keys() - {POSTAL_APPOINTMENT_SOURCE_ID}:
        raise ValueError("Provide the complete set of four baseline pilot originals")
    if include_postal and POSTAL_APPOINTMENT_SOURCE_ID not in source_ids:
        raise ValueError("Preview import requires all five pilot originals")
    for item in originals:
        if item.sha256 != PILOT_SOURCES[item.source_id].content_sha256:
            raise ValueError(f"Original differs from the recorded capture: {item.source_id}")
    return originals


def _store_originals(db: Session, originals: tuple[PreparedOriginal, ...]) -> dict:
    records = {key: source.registry_fields(key) for key, source in PILOT_SOURCES.items()}
    bodies = {item.source_id: (item.body, item.media_type) for item in originals}
    if POSTAL_APPOINTMENT_SOURCE_ID not in bodies:
        postal_version_id = db.scalar(select(KnowledgeSourceVersion.id).where(
            KnowledgeSourceVersion.source_id == POSTAL_APPOINTMENT_SOURCE_ID,
            KnowledgeSourceVersion.revision == 1,
        ))
        if postal_version_id is not None:
            snapshot = db.get(KnowledgeSnapshot, postal_version_id)
            if snapshot is None:
                raise ValueError("Stored Poste version has no original snapshot")
            bodies[POSTAL_APPOINTMENT_SOURCE_ID] = (snapshot.raw_body, snapshot.media_type)
    results = {}
    for source_id, (body, media_type) in bodies.items():
        expected = PILOT_SOURCES[source_id]
        source = db.get(KnowledgeSource, source_id)
        if source is None:
            source = KnowledgeSource(**records[source_id])
            db.add(source)
            db.flush()
        result = ingest_snapshot(
            db, source, body, media_type=media_type,
            retrieved_at=expected.retrieved_at, pilot_review=True,
        )
        version = db.get(KnowledgeSourceVersion, result.version_id)
        retrieved_at = version.retrieved_at
        if retrieved_at.tzinfo is None:
            retrieved_at = retrieved_at.replace(tzinfo=timezone.utc)
        if (
            version.status != "pending_review" or version.revision != 1
            or version.reviewed_at is not None or version.reviewed_by is not None
            or retrieved_at != expected.retrieved_at
            or not verify_snapshot(db, version)
        ):
            raise ValueError(f"Pilot version failed pending review or integrity checks: {source.id}")
        results[source.id] = result

    claims = {}
    for claim_id, references in PILOT_CLAIM_PASSAGES.items():
        if claim_id == "Q3" and POSTAL_APPOINTMENT_SOURCE_ID not in results:
            continue
        passages = []
        for source_id, ordinal, digest in references:
            version_id = results[source_id].version_id
            passage_id = f"{version_id}:{ordinal:04d}"
            passage = db.get(KnowledgePassage, passage_id)
            if passage is None or passage.content_sha256 != digest:
                raise ValueError(f"Passage has changed: {claim_id} {source_id} {ordinal}")
            passages.append({
                "source_id": source_id, "source_version_id": version_id,
                "passage_id": passage_id, "passage_sha256": digest,
            })
        claims[claim_id] = passages
    return {
        "sources": [asdict(result) for result in results.values()],
        "claims_pending_review": claims,
        "claims_pending_acquisition": [] if "Q3" in claims else ["Q3"],
    }


def build_review_catalogue(originals_dir: Path, catalogue: Path) -> dict:
    """Store the four baseline originals and optional Poste evidence in one transaction."""
    originals = _prepare_originals(originals_dir)
    if catalogue.is_symlink() or catalogue.exists() and not catalogue.is_file():
        raise ValueError("Catalogue must be a regular SQLite file")

    engine = create_engine(URL.create("sqlite+pysqlite", database=str(catalogue.resolve())))
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys = ON")
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            _check_database(connection)
            with Session(bind=connection, join_transaction_mode="create_savepoint") as db, db.begin():
                return {"catalogue": str(catalogue.resolve()), **_store_originals(db, originals)}
    finally:
        engine.dispose()


def import_preview_catalogue(originals_dir: Path, database_url: str) -> dict:
    """Import the pinned originals as candidates in one verified Preview transaction."""
    try:
        url = make_url(database_url)
    except ArgumentError:
        raise ValueError("Invalid Preview connection configuration") from None
    require_pilot_preview_target(url)
    originals = _prepare_originals(originals_dir, include_postal=True)
    engine = create_engine(url.set(drivername="postgresql+psycopg"), pool_pre_ping=True)
    try:
        with Session(engine) as db, db.begin():
            require_pilot_preview_database(db)
            return {"catalogue": "preview", **_store_originals(db, originals)}
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--originals", required=True, type=Path)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--catalogue", type=Path)
    target.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    try:
        result = (
            import_preview_catalogue(args.originals, environ.get("DATABASE_URL", "")) if args.preview
            else build_review_catalogue(args.originals, args.catalogue)
        )
        print(json.dumps(result, indent=2))
    except SQLAlchemyError:
        parser.exit(1, "Database operation failed. Check the isolated target and schema.\n")
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
