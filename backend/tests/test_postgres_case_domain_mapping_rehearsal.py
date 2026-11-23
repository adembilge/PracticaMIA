"""Full disposable rehearsal of the legacy case-domain table graph.

The fixture mirrors the current migration inventory and proposed task/conversation
names. It uses synthetic PostgreSQL rows in a random schema only; no application
database, configured keys, production schema, or live data is accessed.
"""
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text

from app.migration_harness.relational import copy_table_rows, assert_owner_consistency
from app.migration_harness.crypto import MigrationQuarantine

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_SMOKE") != "1",
    reason="requires the disposable CI PostgreSQL database",
)


def test_complete_case_domain_graph_copies_to_task_conversation_names():
    engine = create_engine(os.environ["DATABASE_URL"])
    schema = f"m4_domain_{uuid4().hex}"
    try:
        with engine.begin() as c:
            c.execute(text(f'CREATE SCHEMA "{schema}"'))
            # Source graph: current Case/AgentThread table names.
            source_ddl = [
                """CREATE TABLE {s}.cases (
                    id TEXT PRIMARY KEY, owner_subject TEXT NULL, procedure TEXT NOT NULL,
                    status TEXT NOT NULL, scope_answers JSONB NOT NULL, archived_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL, updated_at TIMESTAMPTZ NOT NULL)""",
                """CREATE TABLE {s}.case_intakes (
                    case_id TEXT PRIMARY KEY REFERENCES {s}.cases(id), owner_subject TEXT NOT NULL,
                    facts JSONB NOT NULL, checklist_progress JSONB NOT NULL,
                    progress_fingerprint TEXT, confirmed_at TIMESTAMPTZ, updated_at TIMESTAMPTZ NOT NULL)""",
                """CREATE TABLE {s}.agent_threads (
                    id TEXT PRIMARY KEY, owner_subject TEXT NOT NULL, revision INTEGER NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL)""",
                """CREATE TABLE {s}.agent_thread_cases (
                    thread_id TEXT NOT NULL REFERENCES {s}.agent_threads(id) ON DELETE CASCADE,
                    case_id TEXT NOT NULL REFERENCES {s}.cases(id) ON DELETE CASCADE,
                    PRIMARY KEY(thread_id, case_id))""",
                """CREATE TABLE {s}.agent_run_requests (
                    id TEXT PRIMARY KEY, thread_id TEXT NOT NULL REFERENCES {s}.agent_threads(id) ON DELETE CASCADE,
                    case_id TEXT NULL, client_message_id TEXT NOT NULL, status TEXT NOT NULL,
                    accepted_revision INTEGER NOT NULL, message_ciphertext BYTEA NOT NULL,
                    accepted_at TIMESTAMPTZ NOT NULL, lease_token TEXT, lease_expires_at TIMESTAMPTZ,
                    UNIQUE(thread_id, client_message_id),
                    FOREIGN KEY(thread_id, case_id) REFERENCES {s}.agent_thread_cases(thread_id, case_id),
                    CHECK ((lease_token IS NULL) = (lease_expires_at IS NULL)))""",
                """CREATE TABLE {s}.agent_run_events (
                    run_id TEXT NOT NULL REFERENCES {s}.agent_run_requests(id) ON DELETE CASCADE,
                    event_seq INTEGER NOT NULL CHECK(event_seq > 0), ciphertext BYTEA NOT NULL,
                    PRIMARY KEY(run_id, event_seq))""",
                """CREATE TABLE {s}.agent_run_checkpoints (
                    run_id TEXT PRIMARY KEY REFERENCES {s}.agent_run_requests(id) ON DELETE CASCADE,
                    revision INTEGER NOT NULL CHECK(revision > 0), event_seq INTEGER NOT NULL CHECK(event_seq >= 0),
                    ciphertext BYTEA NOT NULL)""",
                """CREATE TABLE {s}.agent_case_operations (
                    id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES {s}.agent_run_requests(id) ON DELETE CASCADE,
                    case_id TEXT NOT NULL REFERENCES {s}.cases(id) ON DELETE CASCADE,
                    client_operation_id TEXT NOT NULL, proposal_id TEXT NOT NULL,
                    expected_case_revision BIGINT NOT NULL, case_revision BIGINT NOT NULL,
                    UNIQUE(run_id, client_operation_id), UNIQUE(run_id, proposal_id),
                    UNIQUE(case_id, expected_case_revision),
                    CHECK(expected_case_revision > 0 AND case_revision = expected_case_revision + 1))""",
                """CREATE TABLE {s}.private_case_documents (
                    id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES {s}.cases(id) ON DELETE CASCADE,
                    owner_subject TEXT NOT NULL, category TEXT NOT NULL, media_type TEXT NOT NULL,
                    content_sha256 TEXT NOT NULL, ciphertext BYTEA NOT NULL, review_ciphertext BYTEA,
                    consent_version TEXT NOT NULL, consented_at TIMESTAMPTZ NOT NULL,
                    scanned_at TIMESTAMPTZ NOT NULL, uploaded_at TIMESTAMPTZ NOT NULL,
                    expires_at TIMESTAMPTZ NOT NULL)""",
                """CREATE TABLE {s}.case_preparations (
                    case_id TEXT PRIMARY KEY REFERENCES {s}.cases(id) ON DELETE CASCADE,
                    owner_subject TEXT NOT NULL, facts_ciphertext BYTEA NOT NULL,
                    review_digest TEXT, updated_at TIMESTAMPTZ NOT NULL)""",
                """CREATE TABLE {s}.case_documents (
                    id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES {s}.cases(id) ON DELETE CASCADE,
                    owner_subject TEXT NOT NULL, document_type TEXT NOT NULL, media_type TEXT NOT NULL,
                    content_sha256 TEXT NOT NULL, ciphertext BYTEA NOT NULL, review_ciphertext BYTEA NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL)""",
                """CREATE TABLE {s}.case_agent_turns (
                    id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES {s}.cases(id) ON DELETE CASCADE,
                    owner_subject TEXT NOT NULL, content_ciphertext BYTEA NOT NULL,
                    content_sha256 TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL)""",
            ]
            target_ddl = [
                """CREATE TABLE {s}.tasks (
                    id TEXT PRIMARY KEY, owner_subject TEXT NULL, procedure TEXT NOT NULL,
                    status TEXT NOT NULL, scope_answers JSONB NOT NULL, archived_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL, updated_at TIMESTAMPTZ NOT NULL)""",
                """CREATE TABLE {s}.task_intakes (
                    task_id TEXT PRIMARY KEY REFERENCES {s}.tasks(id), owner_subject TEXT NOT NULL,
                    facts JSONB NOT NULL, checklist_progress JSONB NOT NULL,
                    progress_fingerprint TEXT, confirmed_at TIMESTAMPTZ, updated_at TIMESTAMPTZ NOT NULL)""",
                """CREATE TABLE {s}.conversations (
                    id TEXT PRIMARY KEY, owner_subject TEXT NOT NULL, revision INTEGER NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL)""",
                """CREATE TABLE {s}.conversation_tasks (
                    conversation_id TEXT NOT NULL REFERENCES {s}.conversations(id) ON DELETE CASCADE,
                    task_id TEXT NOT NULL REFERENCES {s}.tasks(id) ON DELETE CASCADE,
                    PRIMARY KEY(conversation_id, task_id))""",
                """CREATE TABLE {s}.conversation_runs (
                    id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL REFERENCES {s}.conversations(id) ON DELETE CASCADE,
                    task_id TEXT NULL, client_message_id TEXT NOT NULL, status TEXT NOT NULL,
                    accepted_revision INTEGER NOT NULL, message_ciphertext BYTEA NOT NULL,
                    accepted_at TIMESTAMPTZ NOT NULL, lease_token TEXT, lease_expires_at TIMESTAMPTZ,
                    UNIQUE(conversation_id, client_message_id),
                    FOREIGN KEY(conversation_id, task_id) REFERENCES {s}.conversation_tasks(conversation_id, task_id),
                    CHECK ((lease_token IS NULL) = (lease_expires_at IS NULL)))""",
                """CREATE TABLE {s}.conversation_run_events (
                    run_id TEXT NOT NULL REFERENCES {s}.conversation_runs(id) ON DELETE CASCADE,
                    event_seq INTEGER NOT NULL CHECK(event_seq > 0), ciphertext BYTEA NOT NULL,
                    PRIMARY KEY(run_id, event_seq))""",
                """CREATE TABLE {s}.conversation_run_checkpoints (
                    run_id TEXT PRIMARY KEY REFERENCES {s}.conversation_runs(id) ON DELETE CASCADE,
                    revision INTEGER NOT NULL CHECK(revision > 0), event_seq INTEGER NOT NULL CHECK(event_seq >= 0),
                    ciphertext BYTEA NOT NULL)""",
                """CREATE TABLE {s}.task_operation_receipts (
                    id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES {s}.conversation_runs(id) ON DELETE CASCADE,
                    task_id TEXT NOT NULL REFERENCES {s}.tasks(id) ON DELETE CASCADE,
                    client_operation_id TEXT NOT NULL, proposal_id TEXT NOT NULL,
                    expected_case_revision BIGINT NOT NULL, case_revision BIGINT NOT NULL,
                    UNIQUE(run_id, client_operation_id), UNIQUE(run_id, proposal_id),
                    UNIQUE(task_id, expected_case_revision),
                    CHECK(expected_case_revision > 0 AND case_revision = expected_case_revision + 1))""",
                """CREATE TABLE {s}.private_task_documents (
                    id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES {s}.tasks(id) ON DELETE CASCADE,
                    owner_subject TEXT NOT NULL, category TEXT NOT NULL, media_type TEXT NOT NULL,
                    content_sha256 TEXT NOT NULL, ciphertext BYTEA NOT NULL, review_ciphertext BYTEA,
                    consent_version TEXT NOT NULL, consented_at TIMESTAMPTZ NOT NULL,
                    scanned_at TIMESTAMPTZ NOT NULL, uploaded_at TIMESTAMPTZ NOT NULL,
                    expires_at TIMESTAMPTZ NOT NULL)""",
                """CREATE TABLE {s}.task_preparations (
                    task_id TEXT PRIMARY KEY REFERENCES {s}.tasks(id) ON DELETE CASCADE,
                    owner_subject TEXT NOT NULL, facts_ciphertext BYTEA NOT NULL,
                    review_digest TEXT, updated_at TIMESTAMPTZ NOT NULL)""",
                """CREATE TABLE {s}.task_documents (
                    id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES {s}.tasks(id) ON DELETE CASCADE,
                    owner_subject TEXT NOT NULL, document_type TEXT NOT NULL, media_type TEXT NOT NULL,
                    content_sha256 TEXT NOT NULL, ciphertext BYTEA NOT NULL, review_ciphertext BYTEA NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL)""",
                """CREATE TABLE {s}.task_guide_turns (
                    id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES {s}.tasks(id) ON DELETE CASCADE,
                    owner_subject TEXT NOT NULL, content_ciphertext BYTEA NOT NULL,
                    content_sha256 TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL)""",
            ]
            for statement in source_ddl + target_ddl:
                c.execute(text(statement.format(s=f'"{schema}"')))

            c.execute(text(f"""INSERT INTO "{schema}".cases VALUES
                ('task-1','owner-1','milan_residence_change','draft','[]',NULL,NOW(),NOW()),
                ('legacy-ownerless',NULL,'milan_residence_change','draft','[]',NULL,NOW(),NOW())"""))
            c.execute(text(f"""INSERT INTO "{schema}".agent_threads VALUES ('conv-1','owner-1',9,NOW())"""))
            c.execute(text(f"""INSERT INTO "{schema}".agent_thread_cases VALUES ('conv-1','task-1')"""))
            c.execute(text(f"""INSERT INTO "{schema}".case_intakes VALUES
                ('task-1','owner-1','{{"confirmed":true}}','{{"step":true}}','digest-1',NOW(),NOW())"""))
            c.execute(text(f"""INSERT INTO "{schema}".agent_run_requests VALUES
                ('run-linked','conv-1','task-1','msg-1','completed',9,decode('0102','hex'),NOW(),NULL,NULL),
                ('run-chat','conv-1',NULL,'msg-2','completed',9,decode('0304','hex'),NOW(),NULL,NULL)"""))
            c.execute(text(f"""INSERT INTO "{schema}".agent_run_events VALUES
                ('run-linked',1,decode('0506','hex')), ('run-linked',2,decode('0708','hex'))"""))
            c.execute(text(f"""INSERT INTO "{schema}".agent_run_checkpoints VALUES
                ('run-linked',2,2,decode('090a','hex'))"""))
            c.execute(text(f"""INSERT INTO "{schema}".agent_case_operations VALUES
                ('op-1','run-linked','task-1','client-op-1','proposal-1',4,5)"""))
            c.execute(text(f"""INSERT INTO "{schema}".private_case_documents VALUES
                ('vault-1','task-1','owner-1','identity','application/pdf','hash-vault',
                 decode('0b0c','hex'),decode('0d0e','hex'),'consent-v1',NOW(),NOW(),NOW(),NOW()+INTERVAL '7 days')"""))
            c.execute(text(f"""INSERT INTO "{schema}".case_preparations VALUES
                ('task-1','owner-1',decode('0f10','hex'),'prep-digest',NOW())"""))
            c.execute(text(f"""INSERT INTO "{schema}".case_documents VALUES
                ('doc-1','task-1','owner-1','identity','application/pdf','hash-doc',
                 decode('1112','hex'),decode('1314','hex'),NOW())"""))
            c.execute(text(f"""INSERT INTO "{schema}".case_agent_turns VALUES
                ('turn-1','task-1','owner-1',decode('1516','hex'),'hash-turn',NOW())"""))

        pairs = [
            ("cases","tasks",{}),
            ("agent_threads","conversations",{}),
            ("agent_thread_cases","conversation_tasks",{"thread_id":"conversation_id","case_id":"task_id"}),
            ("case_intakes","task_intakes",{"case_id":"task_id"}),
            ("agent_run_requests","conversation_runs",{"thread_id":"conversation_id","case_id":"task_id"}),
            ("agent_run_events","conversation_run_events",{}),
            ("agent_run_checkpoints","conversation_run_checkpoints",{}),
            ("agent_case_operations","task_operation_receipts",{"case_id":"task_id","expected_case_revision":"expected_case_revision"}),
            ("private_case_documents","private_task_documents",{"case_id":"task_id"}),
            ("case_preparations","task_preparations",{"case_id":"task_id"}),
            ("case_documents","task_documents",{"case_id":"task_id"}),
            ("case_agent_turns","task_guide_turns",{"case_id":"task_id"}),
        ]
        with engine.begin() as c:
            for source, target, mapping in pairs:
                copied = copy_table_rows(c, source_table=f"{schema}.{source}",
                                         target_table=f"{schema}.{target}", column_map=mapping)
                assert copied == (2 if source == "cases" else 2 if source == "agent_run_requests" else 2 if source == "agent_run_events" else 1)
            for child in ("task_intakes","task_preparations","task_documents","task_guide_turns","private_task_documents"):
                assert_owner_consistency(c, child_table=f"{schema}.{child}", parent_table=f"{schema}.tasks",
                                         child_parent_id="task_id", parent_id="id") == 0
            assert c.execute(text(f"""SELECT owner_subject FROM "{schema}".tasks
                WHERE id='legacy-ownerless'""")).scalar_one() is None
            assert c.execute(text(f"""SELECT task_id, message_ciphertext FROM "{schema}".conversation_runs
                WHERE id='run-chat'""")).one() == (None, b"\\x03\\x04")
            assert c.execute(text(f"""SELECT ciphertext FROM "{schema}".private_task_documents
                WHERE id='vault-1'""")).scalar_one() == b"\\x0b\\x0c"
            assert c.execute(text(f"""SELECT ciphertext, review_ciphertext FROM "{schema}".task_documents
                WHERE id='doc-1'""")).one() == (b"\\x11\\x12", b"\\x13\\x14")
            assert c.execute(text(f"""SELECT event_seq FROM "{schema}".conversation_run_events
                WHERE run_id='run-linked' ORDER BY event_seq""")).scalars().all() == [1,2]

        # Quarantine rather than repair an owner mismatch in every denormalized child family.
        with engine.begin() as c:
            c.execute(text(f"""UPDATE "{schema}".task_documents SET owner_subject='foreign-owner'
                WHERE id='doc-1'"""))
        with engine.connect() as c, pytest.raises(MigrationQuarantine) as error:
            assert_owner_consistency(c, child_table=f"{schema}.task_documents",
                                     parent_table=f"{schema}.tasks",
                                     child_parent_id="task_id", parent_id="id")
        assert error.value.code == "relational_owner_boundary_mismatch"
    finally:
        with engine.begin() as c:
            c.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()
