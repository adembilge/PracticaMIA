"""Disposable CI PostgreSQL smoke for additive preview-only preparation storage."""
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.orm import Session

from app.agent.contract import RunStarted, SendMessage
from app.agent.run_events import AgentRunEvent, append_run_event, read_run_events, read_run_snapshot
from app.agent.run_requests import AgentRunRequest, accept_message, read_run_message
from app.agent.threads import AgentThread, AgentThreadCase, create_thread, link_case_to_thread
from app.auth.tokens import Principal
from app.cases.model import CaseRecord
from app.config import Settings
from app.main import create_app
from app.preparation.models import CasePreparation, CaseDocument, CaseAgentTurn
from conftest import AUDIENCE, ISSUER, JWKS_URL

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_SMOKE") != "1",
    reason="requires disposable PG17 CI migrated through 0020",
)


def test_migration_includes_preparation_tables_and_real_cascading_delete(auth_headers):
    database = os.environ["DATABASE_URL"]
    engine = create_engine(database)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "20261118_0020"
        assert {"case_preparations", "case_documents", "case_agent_turns"}.issubset(
            set(inspect(engine).get_table_names())
        )
    finally:
        engine.dispose()
    app = create_app(Settings(
        database_url=database,
        enable_demo_case_api=True,
        enable_knowledge_catalog_api=True,
        enable_preparation_api=True,
        enable_agent_history_api=True,
        deployment_environment="preview",
        preparation_target="isolated_staging",
        preparation_database_fingerprint=sha256(database.encode()).hexdigest(),
        preparation_document_key=base64.b64encode(bytes(range(32))).decode(),
        auth_issuer=ISSUER, auth_audience=AUDIENCE, auth_jwks_url=JWKS_URL,
    ))
    alice = auth_headers("alice")
    try:
        with TestClient(app) as client:
            case = client.post("/api/v1/cases", json={}, headers=alice)
            assert case.status_code == 201, case.text
            case_id = case.json()["id"]
            try:
                facts = client.put(
                    f"/api/v1/cases/{case_id}/preparation/facts",
                    json={"confirmed_facts": {"synthetic_eligibility": "yes"}},
                    headers=alice,
                )
                assert facts.status_code == 200, facts.text
                with app.state.session_factory() as db:
                    row = db.get(CasePreparation, case_id)
                    assert row is not None
                    assert b"synthetic_eligibility" not in row.facts_ciphertext
                guide = client.post(
                    f"/api/v1/cases/{case_id}/preparation/guide",
                    json={"question": "What comes next?"}, headers=alice,
                )
                assert guide.status_code == 200, guide.text
                assert guide.json()["history_saved"] is True
                with app.state.session_factory() as db:
                    turns = db.scalars(select(CaseAgentTurn).where(
                        CaseAgentTurn.case_id == case_id,
                    )).all()
                    assert len(turns) == 1
                    assert b"What comes next?" not in turns[0].content_ciphertext
            finally:
                # Explicit case deletion also exercises database FK behavior.
                assert client.delete(f"/api/v1/cases/{case_id}", headers=alice).status_code == 204
            with app.state.session_factory() as db:
                assert db.get(CasePreparation, case_id) is None
                assert db.scalars(select(CaseDocument).where(
                    CaseDocument.case_id == case_id,
                )).all() == []
                assert db.scalars(select(CaseAgentTurn).where(
                    CaseAgentTurn.case_id == case_id,
                )).all() == []
    finally:
        app.state.engine.dispose()


def test_agent_thread_case_link_is_owned_concurrent_and_cascades():
    engine = create_engine(os.environ["DATABASE_URL"])
    first, second, foreign = uuid4(), uuid4(), uuid4()
    alice, bob = Principal("synthetic-thread-alice"), Principal("synthetic-thread-bob")
    with Session(engine) as db, db.begin():
        db.add_all([
            CaseRecord(id=str(first), owner_subject=alice.subject),
            CaseRecord(id=str(second), owner_subject=alice.subject),
            CaseRecord(id=str(foreign), owner_subject=bob.subject),
        ])
        thread_id = create_thread(db, principal=alice)

    def attach(case_id):
        with Session(engine) as db, db.begin():
            return link_case_to_thread(db, principal=alice, thread_id=thread_id, case_id=case_id)

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            assert list(executor.map(attach, [first, first])) == [True, True]
        assert attach(second)
        assert not attach(foreign)
        with Session(engine) as db, db.begin():
            assert not link_case_to_thread(
                db, principal=bob, thread_id=thread_id, case_id=foreign,
            )
            statement = select(func.count()).select_from(AgentThreadCase).where(
                AgentThreadCase.thread_id == str(thread_id),
            )
            assert db.scalar(statement) == 2
            db.delete(db.get(CaseRecord, str(first)))
            db.flush()
            assert db.scalar(statement) == 1
            db.delete(db.get(AgentThread, str(thread_id)))
            db.flush()
            assert db.scalar(statement) == 0
    finally:
        with Session(engine) as db, db.begin():
            for case_id in (first, second, foreign):
                if record := db.get(CaseRecord, str(case_id)):
                    db.delete(record)
            if thread := db.get(AgentThread, str(thread_id)):
                db.delete(thread)
        engine.dispose()


def test_agent_message_acceptance_serializes_concurrent_retries_and_cascades():
    engine = create_engine(os.environ["DATABASE_URL"])
    owner = Principal("synthetic-run-owner")
    case_id = uuid4()
    key = bytes(range(32))
    with Session(engine) as db, db.begin():
        db.add(CaseRecord(id=str(case_id), owner_subject=owner.subject))
        thread_id = create_thread(db, principal=owner)
        assert link_case_to_thread(db, principal=owner, thread_id=thread_id, case_id=case_id)

    context = {"thread_id": thread_id, "principal": owner, "key": key}
    message = SendMessage(
        client_message_id=uuid4(), case_id=case_id, text="Fixture only", language="en",
    )

    def accept(payload):
        with Session(engine) as db, db.begin():
            return accept_message(db, **context, message=payload)

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            first, retry = executor.map(accept, [message, message])
        assert first.outcome == "accepted"
        assert retry == first
        start = RunStarted(
            schema_version=1, thread_id=thread_id, run_id=first.run_id, event_seq=1,
            occurred_at=datetime.now(timezone.utc), type="run.started",
            client_message_id=message.client_message_id,
        )

        def append_start(_):
            with Session(engine) as db, db.begin():
                return append_run_event(db, principal=owner, key=key, event=start)

        with ThreadPoolExecutor(max_workers=2) as executor:
            assert list(executor.map(append_start, range(2))) == [start, start]

        different = message.model_copy(update={"client_message_id": uuid4()})
        assert accept(different).outcome == "active_run"
        with Session(engine) as db, db.begin():
            rows = db.scalars(select(AgentRunRequest).where(
                AgentRunRequest.thread_id == str(thread_id),
            )).all()
            assert len(rows) == 1
            assert read_run_message(db, **context, run_id=first.run_id).text == message.text
            assert read_run_events(db, **context, run_id=first.run_id, after_seq=0).events == [start]
            assert read_run_snapshot(db, **context, run_id=first.run_id).status == "running"
            db.delete(db.get(CaseRecord, str(case_id)))
            db.flush()
            assert read_run_message(db, **context, run_id=first.run_id) is None
            assert db.scalar(select(AgentRunRequest.id).where(
                AgentRunRequest.id == str(first.run_id),
            )) is None
            assert read_run_events(db, **context, run_id=first.run_id, after_seq=0) is None
            assert db.get(AgentRunEvent, (str(first.run_id), 1)) is None
    finally:
        with Session(engine) as db, db.begin():
            if case := db.get(CaseRecord, str(case_id)):
                db.delete(case)
            if thread := db.get(AgentThread, str(thread_id)):
                db.delete(thread)
        engine.dispose()
