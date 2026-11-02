"""Constraint checks against the migrated database. Synthetic ids only."""
import os

import psycopg
import pytest

DSN = "host=%s port=%s dbname=%s user=%s" % (
    os.environ.get("PAPERPILOT_DB_HOST", "127.0.0.1"),
    os.environ.get("PAPERPILOT_DB_PORT", "5432"),
    os.environ.get("PAPERPILOT_DB_NAME", "paperpilot"),
    os.environ.get("PAPERPILOT_DB_USER", "postgres"),
)


@pytest.fixture
def db():
    conn = psycopg.connect(DSN)
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


def test_second_open_case_fails(db):
    db.execute("INSERT INTO person (id) VALUES ('p-open')")
    db.execute(
        'INSERT INTO "case" (id, person_id, stop, open) VALUES (%s, %s, %s, true)',
        ("c-open-1", "p-open", "not ready"),
    )
    with pytest.raises(psycopg.errors.UniqueViolation):
        db.execute(
            'INSERT INTO "case" (id, person_id, stop, open) VALUES (%s, %s, %s, true)',
            ("c-open-2", "p-open", "not ready"),
        )


def test_second_current_upload_fails(db):
    db.execute("INSERT INTO person (id) VALUES ('p-up')")
    db.execute(
        'INSERT INTO "case" (id, person_id, stop) VALUES (%s, %s, %s)',
        ("c-up", "p-up", "not ready"),
    )
    db.execute(
        "INSERT INTO upload (id, case_id, role, status, current) VALUES (%s, %s, %s, %s, true)",
        ("u-1", "c-up", "title", "read"),
    )
    with pytest.raises(psycopg.errors.UniqueViolation):
        db.execute(
            "INSERT INTO upload (id, case_id, role, status, current) VALUES (%s, %s, %s, %s, true)",
            ("u-2", "c-up", "title", "read"),
        )


def test_failed_upload_rejects_extracted_name(db):
    db.execute("INSERT INTO person (id) VALUES ('p-fail')")
    db.execute(
        'INSERT INTO "case" (id, person_id, stop) VALUES (%s, %s, %s)',
        ("c-fail", "p-fail", "not ready"),
    )
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute(
            "INSERT INTO upload (id, case_id, role, status, extracted_name) VALUES (%s, %s, %s, %s, %s)",
            ("u-fail", "c-fail", "title", "failed", "Ada"),
        )


def test_second_trusted_version_fails(db):
    db.execute("INSERT INTO source_document (id) VALUES ('doc-1')")
    db.execute(
        "INSERT INTO source_version (id, source_document_id, review_status) VALUES (%s, %s, %s)",
        ("ver-1", "doc-1", "trusted"),
    )
    with pytest.raises(psycopg.errors.UniqueViolation):
        db.execute(
            "INSERT INTO source_version (id, source_document_id, review_status) VALUES (%s, %s, %s)",
            ("ver-2", "doc-1", "trusted"),
        )


def test_person_has_no_credential_columns(db):
    rows = db.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'person'
        """
    ).fetchall()
    names = {row[0] for row in rows}
    assert names.isdisjoint({"password", "secret", "credential", "email"})


def test_delete_person_keeps_passage(db):
    db.execute("INSERT INTO person (id) VALUES ('p-del')")
    db.execute(
        'INSERT INTO "case" (id, person_id, stop) VALUES (%s, %s, %s)',
        ("c-del", "p-del", "not ready"),
    )
    db.execute(
        "INSERT INTO audit_event (id, case_id, action) VALUES (%s, %s, %s)",
        ("a-del", "c-del", "opened"),
    )
    db.execute("INSERT INTO source_document (id) VALUES ('doc-del')")
    db.execute(
        "INSERT INTO source_version (id, source_document_id) VALUES (%s, %s)",
        ("ver-del", "doc-del"),
    )
    db.execute(
        "INSERT INTO passage (id, source_version_id, source_id, body) VALUES (%s, %s, %s, %s)",
        ("pass-del", "ver-del", "src-del", "kept"),
    )
    db.execute("DELETE FROM person WHERE id = 'p-del'")
    assert db.execute('SELECT id FROM "case" WHERE id = %s', ("c-del",)).fetchone() is None
    assert db.execute("SELECT id FROM audit_event WHERE id = %s", ("a-del",)).fetchone() is None
    assert db.execute("SELECT id FROM passage WHERE id = %s", ("pass-del",)).fetchone() is not None


def test_passage_body_is_searchable(db):
    db.execute("INSERT INTO source_document (id) VALUES ('doc-fts')")
    db.execute(
        "INSERT INTO source_version (id, source_document_id) VALUES (%s, %s)",
        ("ver-fts", "doc-fts"),
    )
    db.execute(
        "INSERT INTO passage (id, source_version_id, source_id, body) VALUES (%s, %s, %s, %s)",
        ("pass-fts", "ver-fts", "src-fts", "alpha token sample"),
    )
    row = db.execute(
        """
        SELECT id FROM passage
        WHERE id = 'pass-fts' AND body_tsv @@ plainto_tsquery('simple', 'alpha')
        """
    ).fetchone()
    assert row[0] == "pass-fts"


def test_embedding_nearest_neighbor(db):
    db.execute("INSERT INTO source_document (id) VALUES ('doc-vec')")
    db.execute(
        "INSERT INTO source_version (id, source_document_id) VALUES (%s, %s)",
        ("ver-vec", "doc-vec"),
    )
    db.execute(
        "INSERT INTO passage (id, source_version_id, source_id, body) VALUES (%s, %s, %s, %s)",
        ("pass-vec", "ver-vec", "src-vec", "vector"),
    )
    values = [0.0] * 32
    values[0] = 1.0
    literal = "[" + ",".join(str(value) for value in values) + "]"
    db.execute(
        """
        INSERT INTO embedding (passage_id, model_name, embedding_version, vector)
        VALUES (%s, %s, %s, %s::vector)
        """,
        ("pass-vec", "local", "v1", literal),
    )
    row = db.execute(
        "SELECT passage_id FROM embedding ORDER BY vector <=> %s::vector LIMIT 1",
        (literal,),
    ).fetchone()
    assert row[0] == "pass-vec"
