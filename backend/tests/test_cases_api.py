"""HTTP-level case API tests using synthetic data only."""
from uuid import uuid4

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_health_available_with_demo_api_disabled():
    with TestClient(create_app(Settings())) as http:
        assert http.get("/health").json() == {
            "status": "ok",
            "service": "practicamia-backend",
        }
        assert http.post("/api/v1/cases", json={}).status_code == 404


def test_create_get_update_and_delete_demo_case(client):
    created = client.post("/api/v1/cases", json={})
    assert created.status_code == 201
    case = created.json()
    case_id = case["id"]
    assert case["status"] == "draft"
    assert case["scope_answers"] == []

    read = client.get(f"/api/v1/cases/{case_id}")
    assert read.status_code == 200
    assert read.json()["id"] == case_id

    update = client.patch(
        f"/api/v1/cases/{case_id}/scope",
        json={"answers": ["yes", "yes", "yes", "no", "yes"]},
    )
    assert update.status_code == 200
    assert update.json()["status"] == "provisionally_in_scope"

    partial = client.patch(
        f"/api/v1/cases/{case_id}/scope", json={"answers": ["unsure"]}
    )
    assert partial.status_code == 200
    assert partial.json()["status"] == "needs_information"

    assert client.delete(f"/api/v1/cases/{case_id}").status_code == 204
    assert client.get(f"/api/v1/cases/{case_id}").status_code == 404


def test_strict_scope_validation(client):
    case_id = client.post("/api/v1/cases", json={}).json()["id"]
    bad_payloads = (
        {"answers": []},
        {"answers": ["yes"] * 6},
        {"answers": ["maybe"]},
        {"answers": ["yes"], "applicant_name": "Private Person"},
    )
    for payload in bad_payloads:
        assert client.patch(f"/api/v1/cases/{case_id}/scope", json=payload).status_code == 422
    assert client.get(f"/api/v1/cases/{case_id}").json()["scope_answers"] == []


def test_reject_unrecognized_case_creation_fields(client):
    assert client.post("/api/v1/cases", json={"address": "Do not store this"}).status_code == 422


def test_missing_case_returns_404(client):
    unknown = str(uuid4())
    assert client.get(f"/api/v1/cases/{unknown}").status_code == 404
    assert client.patch(f"/api/v1/cases/{unknown}/scope", json={"answers": ["yes"]}).status_code == 404
    assert client.delete(f"/api/v1/cases/{unknown}").status_code == 404


def test_sqlite_case_survives_new_app_instance(client):
    case_id = client.post("/api/v1/cases", json={}).json()["id"]
    original_settings = client.app.state.settings
    # A fresh app instance with a new connection can still read the saved row.
    with TestClient(create_app(original_settings)) as fresh_client:
        response = fresh_client.get(f"/api/v1/cases/{case_id}")
        assert response.status_code == 200
        assert response.json()["id"] == case_id
