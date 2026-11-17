"""Exercise the staged official directory import with fictional workbook rows."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import sqlite3

from openpyxl import Workbook
import pytest

from app.knowledge.directory_import import import_directory
from app.knowledge.directory_workbook import ISTAT_AREA_CODE, ISTAT_AREA_NAME, parse_workbook


def workbook(path, sheet, headers, rows):
    document = Workbook()
    document.active.title = sheet
    document.active.append(headers)
    for row in rows:
        document.active.append(row)
    document.save(path)
    return path


IPA_HEADERS = ("Codice_IPA", "Denominazione_ente", "Acronimo", "Nome_responsabile")
ISTAT_HEADERS = (
    "Codice Regione", "Denominazione Regione", ISTAT_AREA_CODE, ISTAT_AREA_NAME,
    "Tipologia di Unità territoriale sovracomunale", "Codice Comune formato alfanumerico",
    "Denominazione in italiano", "Denominazione altra lingua",
)


def ingest(tmp_path, provider, source, day):
    return import_directory(
        provider=provider, workbook=source, database=tmp_path / "directory.sqlite3",
        acquired_at=f"2026-10-{day:02}T12:00:00Z",
    )


def test_concurrent_retry_has_one_batch_and_preserves_provenance(tmp_path):
    source = workbook(
        tmp_path / "enti.xlsx", "Sheet1", IPA_HEADERS,
        [("TEST1", "Ente di prova", "EP", "Do not copy this field")],
    )
    with ThreadPoolExecutor(max_workers=2) as workers:
        first, second = workers.map(lambda _: ingest(tmp_path, "ipa", source, 1), range(2))
    assert first.batch_id == second.batch_id
    assert {first.status, second.status} == {"imported", "unchanged_batch"}
    assert first.reference_date is None
    assert first.entities_by_kind == {"authority": 1}
    with closing(sqlite3.connect(tmp_path / "directory.sqlite3")) as db:
        assert db.execute("SELECT count(*) FROM directory_entities").fetchone() == (1,)
        assert db.execute(
            "SELECT publisher, resource_url, format FROM directory_batches"
        ).fetchone() == (
            "AgID",
            "https://indicepa.gov.it/ipa-dati/dataset/5baa3eb8-266e-455a-8de8-b1f434c279b2/"
            "resource/d09adf99-dc10-4349-8c53-27b1e5aa97b6/download/enti.xlsx",
            "xlsx",
        )
        assert "Do not copy this field" not in "\n".join(db.iterdump())


def test_istat_preserves_codes_languages_and_typed_namesakes(tmp_path):
    source = workbook(
        tmp_path / "istat.xlsx", "CODICI al 01_09_2026", ISTAT_HEADERS,
        [
            ("01", "Regione di prova", "201", "Valle", 3, "001001", "Valle", "Tal"),
            ("01", "Regione di prova", "201", "Valle", 3, "001002", "Villaggio", None),
            ("01", "Regione di prova", "002", "Monte", 1, "002001", "Valle", None),
        ],
    )
    report = ingest(tmp_path, "istat", source, 1)
    assert report.reference_date == "2026-09-01"
    assert report.entities_by_kind == {"municipality": 3, "province": 2, "region": 1}
    with closing(sqlite3.connect(tmp_path / "directory.sqlite3")) as db:
        namesakes = db.execute(
            """SELECT kind, code, parent_code, alternative_name, area_type, entity_id
               FROM directory_observations WHERE name = 'Valle' ORDER BY kind, code"""
        ).fetchall()
    assert [row[:-1] for row in namesakes] == [
        ("municipality", "001001", "201", "Tal", None),
        ("municipality", "002001", "002", None, None),
        ("province", "201", "01", None, "3"),
    ]
    assert len({row[-1] for row in namesakes}) == 3


def test_rename_keeps_id_while_suspected_recode_and_reappearance_wait(tmp_path):
    first = workbook(
        tmp_path / "first.xlsx", "Sheet1", IPA_HEADERS,
        [("A1", "Ente Vecchio", None), ("B1", "Ente Stabile", None),
         ("C1", "Ente Uscito", None)],
    )
    second = workbook(
        tmp_path / "second.xlsx", "Sheet1", IPA_HEADERS,
        [("A1", "Ente Nuovo", None), ("B2", "Ente Stabile", None), ("D1", "Ente Nuovo Uno", None)],
    )
    third = workbook(
        tmp_path / "third.xlsx", "Sheet1", IPA_HEADERS,
        [("A1", "Ente Nuovo", None), ("B2", "Ente Stabile", None), ("C1", "Altra Entità", None)],
    )
    initial = ingest(tmp_path, "ipa", first, 1)
    revised = ingest(tmp_path, "ipa", second, 2)
    latest = ingest(tmp_path, "ipa", third, 3)
    assert revised.changes == {
        "changed": 1, "review_identity": 1, "possible_inactive": 2, "new": 1,
    }
    with closing(sqlite3.connect(tmp_path / "directory.sqlite3")) as db:
        def observation(batch, code):
            return db.execute(
                """SELECT entity_id, name, change_kind FROM directory_observations
                   WHERE batch_id = ? AND code = ?""", (batch.batch_id, code),
            ).fetchone()

        assert observation(initial, "A1")[0] == observation(revised, "A1")[0]
        assert observation(initial, "A1")[1] == "Ente Vecchio"
        assert observation(revised, "A1")[1] == "Ente Nuovo"
        assert observation(revised, "B2")[0] is None
        assert observation(latest, "B2")[2] == "review_identity"
        assert observation(latest, "C1")[2] == "review_identity"
        links = db.execute(
            """SELECT code, candidate_id FROM directory_identity_candidates
               WHERE batch_id = ? ORDER BY code""", (latest.batch_id,),
        ).fetchall()
        assert links == [
            ("B2", observation(initial, "B1")[0]),
            ("C1", observation(initial, "C1")[0]),
        ]


def test_geography_parent_change_requires_identity_review(tmp_path):
    first = workbook(
        tmp_path / "first.xlsx", "CODICI al 01_09_2026", ISTAT_HEADERS,
        [("01", "Regione", "201", "Valle", 3, "001001", "Comune", None)],
    )
    second = workbook(
        tmp_path / "second.xlsx", "CODICI al 02_09_2026", ISTAT_HEADERS,
        [("01", "Regione", "002", "Monte", 1, "001001", "Comune", None)],
    )
    first_report = ingest(tmp_path, "istat", first, 1)
    second_report = ingest(tmp_path, "istat", second, 2)
    assert first_report.changes == {"new": 3}
    assert second_report.changes == {
        "new": 1, "possible_inactive": 1, "review_identity": 1, "unchanged": 1,
    }


def test_duplicate_bad_format_and_older_snapshot_do_not_create_a_batch(tmp_path):
    first = workbook(
        tmp_path / "first.xlsx", "Sheet1", IPA_HEADERS, [("A1", "Ente A", None)],
    )
    duplicate = workbook(
        tmp_path / "duplicate.xlsx", "Sheet1", IPA_HEADERS,
        [("A1", "Ente A", None), ("A1", "Ente B", None)],
    )
    older = workbook(
        tmp_path / "older.xlsx", "Sheet1", IPA_HEADERS, [("A0", "Ente C", None)],
    )
    ingest(tmp_path, "ipa", first, 2)
    with pytest.raises(ValueError, match="Duplicate"):
        ingest(tmp_path, "ipa", duplicate, 3)
    with pytest.raises(ValueError, match="predates"):
        ingest(tmp_path, "ipa", older, 1)
    with pytest.raises(ValueError, match="dated Istat"):
        parse_workbook("istat", first.read_bytes())
    with closing(sqlite3.connect(tmp_path / "directory.sqlite3")) as db:
        assert db.execute("SELECT count(*) FROM directory_batches").fetchone() == (1,)
