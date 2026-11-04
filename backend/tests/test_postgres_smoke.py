"""Production-like DB smoke test; run only after CI applies Alembic migration."""
import os
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_SMOKE") != "1",
    reason="requires migrated PostgreSQL test database",
)


def test_postgres_case_ownership_and_legacy_migration(token_factory, auth_headers):
    api = create_app(
        Settings(
            database_url=os.environ["DATABASE_URL"],
            enable_demo_case_api=True,
            auth_issuer="https://identity.example.test/",
            auth_audience="https://api.practicamia.example.test",
            auth_jwks_url="https://identity.example.test/.well-known/jwks.json",
        )
    )
    alice = auth_headers("alice")
    bob = auth_headers("bob")
    try:
        with TestClient(api) as client:
            created = client.post("/api/v1/cases", json={}, headers=alice)
            assert created.status_code == 201, created.text
            case_id = created.json()["id"]
            assert UUID(case_id)
            assert client.get(f"/api/v1/cases/{case_id}", headers=bob).status_code == 404
            assert client.get(f"/api/v1/cases/{case_id}", headers=alice).status_code == 200
            updated = client.patch(
                f"/api/v1/cases/{case_id}/scope",
                json={"answers": ["yes", "yes", "yes", "no", "yes"]},
                headers=alice,
            )
            assert updated.status_code == 200, updated.text
            assert updated.json()["status"] == "provisionally_in_scope"
            # A pre-authentication case was seeded by the CI migration step.
            orphan = "00000000-0000-0000-0000-000000000001"
            assert client.get(f"/api/v1/cases/{orphan}", headers=alice).status_code == 404
            assert client.delete(f"/api/v1/cases/{orphan}", headers=alice).status_code == 404
            assert client.delete(f"/api/v1/cases/{case_id}", headers=alice).status_code == 204
    finally:
        api.state.engine.dispose()
