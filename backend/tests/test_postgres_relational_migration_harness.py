"""Disposable PostgreSQL rehearsal for relational conversation/task table copies.

Synthetic rows only. The test creates and drops one random schema and never
connects to application tables or configured production/staging databases.
"""
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text

from app.migration_harness.crypto import MigrationQuarantine
from app.migration_harness.relational import assert_owner_consistency, copy_table_rows

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_SMOKE") != "1",
    reason="requires the disposable CI PostgreSQL database",
)


def test_relational_copy_preserves_null_links_and_quarantines_owner_mismatch():
    engine = create_engine(os.environ["DATABASE_URL"])
    schema = f"m4_relational_{uuid4().hex}"
    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            ddl = [
                f'''CREATE TABLE "{schema}".source_conversations (
                    id TEXT PRIMARY KEY, owner_subject TEXT NOT NULL)''',
                f'''CREATE TABLE "{schema}".source_cases (
                    id TEXT PRIMARY KEY, owner_subject TEXT NULL)''',
                f'''CREATE TABLE "{schema}".source_links (
                    conversation_id TEXT NOT NULL REFERENCES "{schema}".source_conversations(id),
                    case_id TEXT NOT NULL REFERENCES "{schema}".source_cases(id),
                    PRIMARY KEY (conversation_id, case_id))''',
                f'''CREATE TABLE "{schema}".source_runs (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL REFERENCES "{schema}".source_conversations(id),
                    case_id TEXT NULL,
                    owner_subject TEXT NOT NULL,
                    accepted_revision INTEGER NOT NULL,
                    ciphertext BYTEA NOT NULL,
                    FOREIGN KEY (conversation_id, case_id)
                      REFERENCES "{schema}".source_links(conversation_id, case_id))''',
                f'''CREATE TABLE "{schema}".source_intakes (
                    case_id TEXT PRIMARY KEY REFERENCES "{schema}".source_cases(id),
                    owner_subject TEXT NOT NULL, facts JSONB NOT NULL)''',
                f'''CREATE TABLE "{schema}".conversations (
                    id TEXT PRIMARY KEY, owner_subject TEXT NOT NULL)''',
                f'''CREATE TABLE "{schema}".tasks (
                    id TEXT PRIMARY KEY, owner_subject TEXT NULL)''',
                f'''CREATE TABLE "{schema}".conversation_tasks (
                    conversation_id TEXT NOT NULL REFERENCES "{schema}".conversations(id),
                    task_id TEXT NOT NULL REFERENCES "{schema}".tasks(id),
                    PRIMARY KEY (conversation_id, task_id))''',
                f'''CREATE TABLE "{schema}".conversation_runs (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL REFERENCES "{schema}".conversations(id),
                    task_id TEXT NULL,
                    owner_subject TEXT NOT NULL,
                    accepted_revision INTEGER NOT NULL,
                    ciphertext BYTEA NOT NULL,
                    FOREIGN KEY (conversation_id, task_id)
                      REFERENCES "{schema}".conversation_tasks(conversation_id, task_id))''',
                f'''CREATE TABLE "{schema}".task_intakes (
                    task_id TEXT PRIMARY KEY REFERENCES "{schema}".tasks(id),
                    owner_subject TEXT NOT NULL, facts JSONB NOT NULL)''',
            ]
            for statement in ddl:
                connection.execute(text(statement))
            connection.execute(text(
                f'''INSERT INTO "{schema}".source_conversations VALUES ('conversation-1', 'owner-1')'''
            ))
            connection.execute(text(
                f'''INSERT INTO "{schema}".source_cases VALUES
                    ('task-1', 'owner-1'), ('legacy-ownerless', NULL)'''
            ))
            connection.execute(text(
                f'''INSERT INTO "{schema}".source_links VALUES ('conversation-1', 'task-1')'''
            ))
            connection.execute(text(
                f'''INSERT INTO "{schema}".source_runs VALUES
                    ('run-linked', 'conversation-1', 'task-1', 'owner-1', 7, decode('010203', 'hex')),
                    ('run-chat', 'conversation-1', NULL, 'owner-1', 8, decode('040506', 'hex'))'''
            ))
            connection.execute(text(
                f'''INSERT INTO "{schema}".source_intakes VALUES
                    ('task-1', 'owner-1', '{{"confirmed": true}}')'''
            ))

        with engine.begin() as connection:
            assert copy_table_rows(
                connection, source_table=f"{schema}.source_conversations",
                target_table=f"{schema}.conversations",
            ) == 1
            assert copy_table_rows(
                connection, source_table=f"{schema}.source_cases",
                target_table=f"{schema}.tasks",
            ) == 2
            assert copy_table_rows(
                connection, source_table=f"{schema}.source_links",
                target_table=f"{schema}.conversation_tasks",
                column_map={"case_id": "task_id"},
            ) == 1
            assert copy_table_rows(
                connection, source_table=f"{schema}.source_runs",
                target_table=f"{schema}.conversation_runs",
                column_map={"case_id": "task_id"},
            ) == 2
            assert copy_table_rows(
                connection, source_table=f"{schema}.source_intakes",
                target_table=f"{schema}.task_intakes",
                column_map={"case_id": "task_id"},
            ) == 1
            assert_owner_consistency(
                connection, child_table=f"{schema}.task_intakes",
                parent_table=f"{schema}.tasks", child_parent_id="task_id", parent_id="id",
            ) == 0
            rows = connection.execute(text(
                f'''SELECT id, task_id, ciphertext FROM "{schema}".conversation_runs ORDER BY id'''
            )).all()
            assert rows == [
                ("run-chat", None, b"\\x04\\x05\\x06"),
                ("run-linked", "task-1", b"\\x01\\x02\\x03"),
            ]

        # A mismatch must stop the rehearsal; it is never auto-repaired.
        with engine.begin() as connection:
            connection.execute(text(
                f'''UPDATE "{schema}".task_intakes SET owner_subject='owner-foreign' WHERE task_id='task-1' '''
            ))
        with engine.connect() as connection:
            with pytest.raises(MigrationQuarantine) as error:
                assert_owner_consistency(
                    connection, child_table=f"{schema}.task_intakes",
                    parent_table=f"{schema}.tasks", child_parent_id="task_id", parent_id="id",
                )
            assert error.value.code == "relational_owner_boundary_mismatch"
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()
