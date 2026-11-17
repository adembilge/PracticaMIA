"""Import official directory snapshots into a local review database."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import sqlite3
from uuid import uuid4
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile, ZipFile

from openpyxl.utils.exceptions import InvalidFileException

from app.knowledge.directory_workbook import PARSER_VERSION, SOURCES, DirectoryRow, parse_workbook
from app.knowledge.entity_matching import normalize_name

MAX_WORKBOOK_BYTES = 20 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 160 * 1024 * 1024

SCHEMA = """
CREATE TABLE IF NOT EXISTS directory_batches (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    publisher TEXT NOT NULL,
    dataset TEXT NOT NULL,
    landing_url TEXT NOT NULL,
    resource_url TEXT NOT NULL,
    format TEXT NOT NULL CHECK (format = 'xlsx'),
    reference_date TEXT,
    acquired_at TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    parser_version TEXT NOT NULL,
    UNIQUE (provider, sha256, parser_version)
);
CREATE TABLE IF NOT EXISTS directory_entities (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS directory_observations (
    batch_id TEXT NOT NULL REFERENCES directory_batches(id),
    kind TEXT NOT NULL,
    code TEXT NOT NULL,
    entity_id TEXT REFERENCES directory_entities(id),
    name TEXT NOT NULL,
    parent_code TEXT,
    alternative_name TEXT,
    acronym TEXT,
    area_type TEXT,
    change_kind TEXT NOT NULL CHECK (change_kind IN (
        'new', 'unchanged', 'changed', 'possible_inactive', 'review_identity'
    )),
    PRIMARY KEY (batch_id, kind, code)
);
CREATE INDEX IF NOT EXISTS ix_directory_observations_code
    ON directory_observations (kind, code);
CREATE TABLE IF NOT EXISTS directory_identity_candidates (
    batch_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    code TEXT NOT NULL,
    candidate_id TEXT NOT NULL REFERENCES directory_entities(id),
    PRIMARY KEY (batch_id, kind, code, candidate_id),
    FOREIGN KEY (batch_id, kind, code)
        REFERENCES directory_observations (batch_id, kind, code)
);
"""


@dataclass(frozen=True)
class ImportReport:
    batch_id: str
    status: str
    provider: str
    source_sha256: str
    reference_date: str | None
    acquired_at: str
    ingested_at: str
    entities_by_kind: dict[str, int]
    changes: dict[str, int]


def _checked_workbook(path: Path) -> bytes:
    with path.open("rb") as workbook:
        contents = workbook.read(MAX_WORKBOOK_BYTES + 1)
    if len(contents) > MAX_WORKBOOK_BYTES:
        raise ValueError("Workbook exceeds the compressed size limit")
    with ZipFile(BytesIO(contents)) as archive:
        entries = archive.infolist()
        if len(entries) > 100 or sum(entry.file_size for entry in entries) > MAX_UNCOMPRESSED_BYTES:
            raise ValueError("Workbook exceeds the expanded size limit")
    return contents


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("Acquisition time must have a UTC offset")
    result = parsed.astimezone(timezone.utc)
    if result > datetime.now(timezone.utc):
        raise ValueError("Acquisition time cannot be in the future")
    return result


def _observation(row: sqlite3.Row) -> DirectoryRow:
    return DirectoryRow(*(row[field] for field in DirectoryRow.__dataclass_fields__))


def _report(db: sqlite3.Connection, batch: sqlite3.Row, status: str) -> ImportReport:
    counts: Counter = Counter()
    changes: Counter = Counter()
    for row in db.execute(
        """SELECT kind, change_kind, count(*) AS total
           FROM directory_observations WHERE batch_id = ? GROUP BY kind, change_kind""",
        (batch["id"],),
    ):
        if row["change_kind"] != "possible_inactive":
            counts[row["kind"]] += row["total"]
        changes[row["change_kind"]] += row["total"]
    return ImportReport(
        batch["id"], status, batch["provider"], batch["sha256"], batch["reference_date"],
        batch["acquired_at"], batch["ingested_at"], dict(counts), dict(changes),
    )


def _record_batch(
    db: sqlite3.Connection, *, provider: str, digest: str, release: str | None,
    acquired: str, rows: list[DirectoryRow],
) -> ImportReport:
    same_batch = db.execute(
        "SELECT * FROM directory_batches WHERE provider = ? AND sha256 = ? AND parser_version = ?",
        (provider, digest, PARSER_VERSION),
    ).fetchone()
    if same_batch:
        return _report(db, same_batch, "unchanged_batch")

    previous = db.execute(
        "SELECT * FROM directory_batches WHERE provider = ? ORDER BY acquired_at DESC LIMIT 1",
        (provider,),
    ).fetchone()
    if previous and (acquired <= previous["acquired_at"] or (
        previous["reference_date"] and release and release < previous["reference_date"]
    )):
        raise ValueError("Workbook predates the latest imported snapshot")

    batch_id = str(uuid4())
    db.execute(
        """INSERT INTO directory_batches VALUES (?, ?, ?, ?, ?, ?, 'xlsx', ?, ?, ?, ?, ?)""",
        (batch_id, provider, *SOURCES[provider], release, acquired,
         datetime.now(timezone.utc).isoformat(timespec="microseconds"), digest, PARSER_VERSION),
    )

    prior = {}
    if previous:
        prior = {
            (record["kind"], record["code"]): record for record in db.execute(
                """SELECT * FROM directory_observations WHERE batch_id = ?
                   AND change_kind != 'possible_inactive'""", (previous["id"],),
            )
        }
    current_keys = {(row.kind, row.code) for row in rows}
    removed = [record for key, record in prior.items() if key not in current_keys]
    removed_by_name: dict[tuple[str, str], set[str]] = defaultdict(set)
    for record in removed:
        if record["entity_id"]:
            removed_by_name[(record["kind"], normalize_name(record["name"]))].add(record["entity_id"])

    for row in rows:
        existing = prior.get((row.kind, row.code))
        candidates = set()
        if existing and existing["entity_id"] and existing["parent_code"] == row.parent_code:
            entity_id = existing["entity_id"]
            change = "unchanged" if _observation(existing) == row else "changed"
        else:
            for record in db.execute(
                """SELECT DISTINCT x.entity_id, candidate.candidate_id
                   FROM directory_observations x
                   JOIN directory_batches b ON b.id = x.batch_id
                   LEFT JOIN directory_identity_candidates candidate ON
                       candidate.batch_id = x.batch_id AND candidate.kind = x.kind
                       AND candidate.code = x.code
                   WHERE b.provider = ? AND x.kind = ? AND x.code = ?""",
                (provider, row.kind, row.code),
            ):
                candidates.update(value for value in record if value)
            candidates.update(removed_by_name.get((row.kind, normalize_name(row.name)), ()))
            if candidates or existing:
                entity_id, change = None, "review_identity"
            else:
                entity_id, change = str(uuid4()), "new"
                db.execute("INSERT INTO directory_entities VALUES (?, ?)", (entity_id, row.kind))
        _insert_observation(db, batch_id, row, entity_id, change)
        db.executemany(
            "INSERT INTO directory_identity_candidates VALUES (?, ?, ?, ?)",
            ((batch_id, row.kind, row.code, candidate) for candidate in sorted(candidates)),
        )
    for record in removed:
        _insert_observation(db, batch_id, _observation(record), record["entity_id"], "possible_inactive")
    batch = db.execute("SELECT * FROM directory_batches WHERE id = ?", (batch_id,)).fetchone()
    return _report(db, batch, "imported")


def _insert_observation(
    db: sqlite3.Connection, batch_id: str, row: DirectoryRow,
    entity_id: str | None, change: str,
) -> None:
    db.execute(
        "INSERT INTO directory_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (batch_id, row.kind, row.code, entity_id, row.name, row.parent_code,
         row.alternative_name, row.acronym, row.area_type, change),
    )


def import_directory(
    *, provider: str, workbook: Path, database: Path, acquired_at: str,
    reference_date: date | None = None,
) -> ImportReport:
    acquired = _timestamp(acquired_at)
    contents = _checked_workbook(workbook)
    workbook_date, rows = parse_workbook(provider, contents)
    if workbook_date and reference_date and workbook_date != reference_date:
        raise ValueError("Provided reference date does not match the workbook")
    release = workbook_date or reference_date
    if release and release > acquired.date():
        raise ValueError("Reference date cannot follow the acquisition date")
    with closing(sqlite3.connect(database, timeout=20, isolation_level=None)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        db.executescript(SCHEMA)
        with db:
            db.execute("BEGIN IMMEDIATE")
            return _record_batch(
                db, provider=provider, digest=sha256(contents).hexdigest(),
                release=release.isoformat() if release else None,
                acquired=acquired.isoformat(timespec="microseconds"), rows=rows,
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("provider", choices=SOURCES)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--database", type=Path, required=True, help="Local SQLite file")
    parser.add_argument("--acquired-at", required=True, help="ISO 8601 timestamp with offset")
    parser.add_argument("--reference-date", type=date.fromisoformat)
    args = parser.parse_args()
    try:
        result = import_directory(**vars(args))
    except (ValueError, OSError, BadZipFile, ParseError, InvalidFileException, sqlite3.Error) as error:
        parser.exit(1, f"Directory import failed: {error}\n")
    print(json.dumps(asdict(result), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
