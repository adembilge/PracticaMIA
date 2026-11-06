"""Disposable CI PostgreSQL smoke for additive preview-only preparation storage."""
import base64
import os
from hashlib import sha256

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select, text

from app.config import Settings
from app.main import create_app
from app.preparation.models import CasePreparation, CaseDocument
from conftest import AUDIENCE, ISSUER, JWKS_URL

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_SMOKE") != "1",
    reason="requires disposable PG17 CI migrated through 0011",
)


def test_migration_includes_preparation_tables_and_real_cascading_delete(auth_headers):
    database = os.environ["DATABASE_URL"]
    engine = create_engine(database)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "20261106_0011"
        assert {"case_preparations", "case_documents"}.issubset(
            set(inspect(engine).get_table_names())
        )
    finally:
        engine.dispose()
    app = create_app(Settings(
        database_url=database,
        enable_demo_case_api=True,
        enable_knowledge_catalog_api=True,
        enable_preparation_api=True,
        deployment_environment="preview",
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
            finally:
                # Explicit case deletion also exercises database FK behavior.
                assert client.delete(f"/api/v1/cases/{case_id}", headers=alice).status_code == 204
            with app.state.session_factory() as db:
                assert db.get(CasePreparation, case_id) is None
                assert db.scalars(select(CaseDocument).where(
                    CaseDocument.case_id == case_id,
                )).all() == []
    finally:
        app.state.engine.dispose()
