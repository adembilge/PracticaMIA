"""Authentication, authorization and persistent synthetic-case HTTP tests."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.cases.model import CaseRecord
from app.config import Settings
from app.main import create_app
from conftest import AUDIENCE, ISSUER, JWKS_URL


def test_health_available_with_case_api_disabled():
    with TestClient(create_app(Settings())) as http:
        assert http.get("/health").json() == {
            "status": "ok",
            "service": "practicamia-backend",
        }
        assert http.post("/api/v1/cases", json={}).status_code == 404


@pytest.mark.parametrize("endpoint,method", [
    ("/api/v1/cases", "POST"),
    ("/api/v1/cases", "GET"),
    (f"/api/v1/cases/{uuid4()}", "GET"),
    (f"/api/v1/cases/{uuid4()}/scope", "PATCH"),
    (f"/api/v1/cases/{uuid4()}", "DELETE"),
])
def test_all_case_routes_require_bearer_token(client, endpoint, method):
    response = client.request(method, endpoint, headers={"X-User-Id": "alice"})
    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"


def test_create_read_update_delete_and_list_owned_case(client, auth_headers):
    alice = auth_headers("alice")
    created = client.post("/api/v1/cases", json={}, headers=alice)
    assert created.status_code == 201, created.text
    case = created.json()
    case_id = case["id"]
    assert case["status"] == "draft"
    assert case["scope_answers"] == []
    assert "owner_subject" not in case

    cases = client.get("/api/v1/cases", headers=alice)
    assert cases.status_code == 200
    assert [item["id"] for item in cases.json()] == [case_id]

    assert client.get(f"/api/v1/cases/{case_id}", headers=alice).status_code == 200
    update = client.patch(
        f"/api/v1/cases/{case_id}/scope",
        json={"answers": ["yes", "yes", "yes", "no", "yes"]},
        headers=alice,
    )
    assert update.status_code == 200
    assert update.json()["status"] == "provisionally_in_scope"

    partial = client.patch(
        f"/api/v1/cases/{case_id}/scope",
        json={"answers": ["unsure"]},
        headers=alice,
    )
    assert partial.status_code == 200
    assert partial.json()["status"] == "needs_information"

    assert client.delete(f"/api/v1/cases/{case_id}", headers=alice).status_code == 204
    assert client.get(f"/api/v1/cases/{case_id}", headers=alice).status_code == 404
    assert client.get("/api/v1/cases", headers=alice).json() == []


def test_cases_are_strictly_isolated_between_users(client, auth_headers):
    alice = auth_headers("alice")
    bob = auth_headers("bob")
    case_id = client.post("/api/v1/cases", json={}, headers=alice).json()["id"]

    assert client.get("/api/v1/cases", headers=bob).json() == []
    assert client.get(f"/api/v1/cases/{case_id}", headers=bob).status_code == 404
    assert client.patch(
        f"/api/v1/cases/{case_id}/scope",
        json={"answers": ["yes", "yes", "yes", "no", "yes"]},
        headers=bob,
    ).status_code == 404
    assert client.delete(f"/api/v1/cases/{case_id}", headers=bob).status_code == 404
    assert client.get(f"/api/v1/cases/{case_id}", headers=alice).status_code == 200
    assert client.delete(f"/api/v1/cases/{case_id}", headers=alice).status_code == 204


@pytest.mark.parametrize("overrides", [
    {"iss": "https://another-issuer.example.test/"},
    {"aud": "https://unrelated-api.example.test"},
    {"exp": datetime.now(timezone.utc) - timedelta(minutes=3)},
    {"iat": datetime.now(timezone.utc) + timedelta(minutes=5)},
    {"sub": ""},
    {"sub": "x" * 256},
])
def test_invalid_claims_are_rejected(client, token_factory, overrides):
    token = token_factory("alice", overrides)
    response = client.post("/api/v1/cases", json={}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_invalid_signature_and_disallowed_algorithm_are_rejected(client, token_factory):
    invalid_signer = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    wrong_signature = token_factory("alice", signing_key=invalid_signer)
    assert client.post(
        "/api/v1/cases", json={}, headers={"Authorization": f"Bearer {wrong_signature}"}
    ).status_code == 401

    unsigned = jwt.encode(
        {"iss": ISSUER, "aud": AUDIENCE, "sub": "alice", "exp": datetime.now(timezone.utc) + timedelta(minutes=5), "iat": datetime.now(timezone.utc)},
        key=None,
        algorithm="none",
        headers={"kid": "unit-test-rsa-key"},
    )
    assert client.post(
        "/api/v1/cases", json={}, headers={"Authorization": f"Bearer {unsigned}"}
    ).status_code == 401


def test_strict_payload_validation(client, auth_headers):
    alice = auth_headers()
    assert client.post(
        "/api/v1/cases", json={"address": "Do not store this"}, headers=alice
    ).status_code == 422
    case_id = client.post("/api/v1/cases", json={}, headers=alice).json()["id"]
    for payload in (
        {"answers": []},
        {"answers": ["yes"] * 6},
        {"answers": ["maybe"]},
        {"answers": ["yes"], "applicant_name": "Private Person"},
    ):
        assert client.patch(
            f"/api/v1/cases/{case_id}/scope", json=payload, headers=alice
        ).status_code == 422
    assert client.get(f"/api/v1/cases/{case_id}", headers=alice).json()["scope_answers"] == []


def test_missing_and_legacy_ownerless_cases_are_not_visible(client, auth_headers):
    alice = auth_headers()
    case_id = str(uuid4())
    with client.app.state.session_factory() as db:
        db.add(CaseRecord(id=case_id, owner_subject=None))
        db.commit()

    assert client.get("/api/v1/cases", headers=alice).json() == []
    assert client.get(f"/api/v1/cases/{case_id}", headers=alice).status_code == 404
    assert client.delete(f"/api/v1/cases/{case_id}", headers=alice).status_code == 404
    assert client.get(f"/api/v1/cases/{uuid4()}", headers=alice).status_code == 404


def test_saved_case_survives_new_app_instance(client, auth_headers):
    alice = auth_headers()
    case_id = client.post("/api/v1/cases", json={}, headers=alice).json()["id"]
    settings = client.app.state.settings
    with TestClient(create_app(settings)) as fresh_client:
        assert fresh_client.get(f"/api/v1/cases/{case_id}", headers=alice).status_code == 200
        assert fresh_client.get(f"/api/v1/cases/{case_id}", headers=auth_headers("bob")).status_code == 404


@pytest.mark.parametrize("missing_key", ["auth_issuer", "auth_audience", "auth_jwks_url"])
def test_case_api_refuses_missing_auth_configuration(missing_key):
    kwargs = dict(database_url="sqlite+pysqlite:///ignored.db", enable_demo_case_api=True,
                  auth_issuer=ISSUER, auth_audience=AUDIENCE, auth_jwks_url=JWKS_URL)
    kwargs[missing_key] = ""
    with pytest.raises(ValueError, match=missing_key.upper()):
        create_app(Settings(**kwargs))


def test_case_api_refuses_unencrypted_jwks_url():
    with pytest.raises(ValueError, match="HTTPS"):
        create_app(Settings(database_url="sqlite+pysqlite:///ignored.db", enable_demo_case_api=True,
                            auth_issuer=ISSUER, auth_audience=AUDIENCE,
                            auth_jwks_url="http://untrusted.example.test/keys"))
