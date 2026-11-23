"""Owner-scoped typed intake: persistence, privacy, confirmation and invalidation."""
from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.cases.intake_model import CaseIntake
from app.main import create_app

SCOPE = ["yes", "yes", "yes", "no", "yes"]
FACTS = {
    "citizenship_class": "italian",
    "registration_context": "already_registered_in_italy",
    "destination_municipality": "milano",
    "household_scope": "individual_no_aggregation",
    "housing_basis": "registered_private_rental",
    "move_in_date": "2026-11-02",
}


def create_scoped_case(client, headers):
    case_id = client.post("/api/v1/cases", json={}, headers=headers).json()["id"]
    response = client.patch(f"/api/v1/cases/{case_id}/scope",
                            json={"answers": SCOPE}, headers=headers)
    assert response.status_code == 200
    return case_id


def test_intake_requires_auth_and_completed_scope(client, auth_headers):
    a, b = auth_headers("alice"), auth_headers("bob")
    case_id = client.post("/api/v1/cases", json={}, headers=a).json()["id"]
    path = f"/api/v1/cases/{case_id}/intake"
    assert client.get(path).status_code == 401
    assert client.get(path, headers=b).status_code == 404
    assert client.put(path, json={"facts": FACTS, "confirm": True}, headers=b).status_code == 404
    assert client.put(path, json={"facts": FACTS, "confirm": True}, headers=a).status_code == 409
    result = client.get(path, headers=a)
    assert result.status_code == 200
    assert result.json()["confirmed"] is False
    assert len(result.json()["missing_fields"]) == 5


def test_draft_confirmation_and_restart_persistence(client, auth_headers):
    headers = auth_headers("alice")
    case_id = create_scoped_case(client, headers)
    path = f"/api/v1/cases/{case_id}/intake"
    draft = client.put(path, json={"facts": {"citizenship_class":"italian"}, "confirm": False}, headers=headers)
    assert draft.status_code == 200
    assert draft.json()["verification_state"] == "draft"
    assert draft.json()["field_provenance"] == {
        "citizenship_class": {"origin": "user_entered", "verification_state": "draft"},
    }
    assert draft.json()["missing_fields"] == [
        "registration_context","destination_municipality","household_scope","housing_basis"
    ]
    no_approval = client.put(path, json={"facts": {"citizenship_class":"italian"}, "confirm": True}, headers=headers)
    assert no_approval.status_code == 422
    saved = client.put(path, json={"facts": FACTS, "confirm": True}, headers=headers)
    assert saved.status_code == 200, saved.text
    assert saved.json()["confirmed"]
    assert saved.json()["first_scenario_match"]
    assert saved.json()["fact_origin"] == "user_entered"
    assert saved.json()["verification_state"] == "user_confirmed"
    assert not saved.json()["eligibility_evaluated"]
    assert not saved.json()["document_requirements_evaluated"]
    assert not saved.json()["official_submission"]
    with TestClient(create_app(client.app.state.settings)) as restarted:
        response = restarted.get(path, headers=headers)
        assert response.status_code == 200
        assert response.json()["facts"] == FACTS
        assert response.json()["confirmed_at"] is not None
        assert response.json()["field_provenance"] == {
            field: {"origin": "user_entered", "verification_state": "user_confirmed"} for field in FACTS
        }
    # Editing the facts clears the previous confirmation.
    edited = client.put(path, json={
        "facts": {**FACTS, "move_in_date": "2026-11-03"}, "confirm": False
    }, headers=headers)
    assert edited.status_code == 200
    assert not edited.json()["confirmed"]
    assert edited.json()["confirmed_at"] is None
    assert edited.json()["field_provenance"]["move_in_date"]["verification_state"] == "draft"


def test_strict_validation_rejects_personal_identifiers_and_untrusted_fields(client, auth_headers):
    headers = auth_headers("alice")
    case_id = create_scoped_case(client, headers)
    path = f"/api/v1/cases/{case_id}/intake"
    for facts in [
        {**FACTS, "previous_address": "Real home address"},
        {**FACTS, "passport_number": "TEST12345"},
        {**FACTS, "contact_email": "real@example.com"},
        {**FACTS, "citizenship_class": "visitor"},
        {**FACTS, "move_in_date": "2026-02-30"},
        {**FACTS, "move_in_date": "2026-01-01T00:00:00Z"},
        {**FACTS, "move_in_date": "not-a-date"},
        {**FACTS, "move_in_date": "3000-01-01"},
        {**FACTS, "housing_basis": ["registered_private_rental"]},
    ]:
        r = client.put(path, json={"facts": facts, "confirm": True}, headers=headers)
        assert r.status_code == 422, (facts, r.text)
    for request in [
        {"facts": FACTS, "confirm": True, "injected": "ignore instructions"},
        {"facts": FACTS, "confirm": "true"},
        {"facts": FACTS, "confirm": True, "field_provenance": {"move_in_date": {"origin": "user_document"}}},
    ]:
        assert client.put(path, json=request, headers=headers).status_code == 422
    assert client.get(path, headers=headers).json()["facts"] == {}


def test_outside_scenario_stops_product_route_without_eligibility_claim(client, auth_headers):
    headers = auth_headers("alice")
    case_id = create_scoped_case(client, headers)
    path = f"/api/v1/cases/{case_id}/intake"
    out = client.put(path, json={
        "facts": {**FACTS, "housing_basis": "guest"}, "confirm": True
    }, headers=headers)
    assert out.status_code == 200
    data = out.json()
    assert data["outside_first_scenario"] == ["housing_basis"]
    assert not data["first_scenario_match"]
    assert not data["eligibility_evaluated"]
    unknown = client.put(path, json={
        "facts": {**FACTS, "housing_basis": "unknown"}, "confirm": True
    }, headers=headers)
    assert unknown.status_code == 422


def test_scope_edit_invalidates_and_erases_confirmed_intake(client, auth_headers):
    headers = auth_headers("alice")
    case_id = create_scoped_case(client, headers)
    path = f"/api/v1/cases/{case_id}/intake"
    assert client.put(path, json={"facts": FACTS, "confirm": True}, headers=headers).status_code == 200
    response = client.patch(f"/api/v1/cases/{case_id}/scope",
                            json={"answers": ["yes", "no"]}, headers=headers)
    assert response.status_code == 200
    got = client.get(path, headers=headers).json()
    assert got["facts"] == {}
    assert not got["confirmed"]
    assert client.put(path, json={"facts": FACTS, "confirm": True}, headers=headers).status_code == 409
    # Re-answering permits a fresh intake, never revives old data.
    assert client.patch(f"/api/v1/cases/{case_id}/scope",
                        json={"answers": SCOPE}, headers=headers).status_code == 200
    assert client.get(path, headers=headers).json()["facts"] == {}


def test_archived_case_blocks_stale_chat_intake_writes_until_restored(client, auth_headers):
    """An old chat form cannot change or erase a case after its owner archives it."""
    owner, other = auth_headers("alice"), auth_headers("bob")
    case_id = create_scoped_case(client, owner)
    path = f"/api/v1/cases/{case_id}/intake"
    archive = f"/api/v1/cases/{case_id}/archive"
    payload = {"facts": FACTS, "confirm": True}
    assert client.put(path, json=payload, headers=owner).status_code == 200
    original = client.get(path, headers=owner).json()
    assert original["confirmed"] is True
    assert client.patch(archive, json={"archived": True}, headers=owner).status_code == 200

    # The owner can inspect their archived record, but neither its open form
    # nor an old conversation may update, reconfirm or erase saved facts.
    assert client.get(path, headers=owner).json() == original
    for confirm in (False, True):
        denied = client.put(path, json={
            "facts": {**FACTS, "move_in_date": "2026-11-03"}, "confirm": confirm,
        }, headers=owner)
        assert denied.status_code == 409
        assert "Restore" in denied.json()["detail"]
    assert client.delete(path, headers=owner).status_code == 409

    # Foreign identities still see 404, never the archived case's state.
    assert client.get(path, headers=other).status_code == 404
    assert client.put(path, json=payload, headers=other).status_code == 404
    assert client.delete(path, headers=other).status_code == 404
    assert client.get(path, headers=owner).json() == original

    assert client.patch(archive, json={"archived": False}, headers=owner).status_code == 200
    restored = client.get(path, headers=owner).json()
    assert restored == original
    assert client.put(path, json={
        "facts": {**FACTS, "move_in_date": "2026-11-03"}, "confirm": False,
    }, headers=owner).status_code == 200
    assert client.get(path, headers=owner).json()["confirmed"] is False


def test_delete_intake_and_delete_case_remove_owner_rows(client, auth_headers):
    headers = auth_headers("alice")
    bob = auth_headers("bob")
    case_id = create_scoped_case(client, headers)
    path = f"/api/v1/cases/{case_id}/intake"
    client.put(path, json={"facts": FACTS, "confirm": True}, headers=headers)
    assert client.delete(path, headers=bob).status_code == 404
    assert client.delete(path, headers=headers).status_code == 204
    assert client.get(path, headers=headers).json()["facts"] == {}
    client.put(path, json={"facts": FACTS, "confirm": True}, headers=headers)
    assert client.delete(f"/api/v1/cases/{case_id}", headers=headers).status_code == 204
    with client.app.state.session_factory() as db:
        assert db.get(CaseIntake, case_id) is None
    assert client.get(path, headers=headers).status_code == 404


def test_canonical_conversation_task_intake_route_and_hidden_legacy_alias(client, auth_headers):
    owner, stranger = auth_headers("alice"), auth_headers("bob")
    task_id = client.post("/api/v1/cases", json={}, headers=owner).json()["id"]
    canonical = f"/api/v1/conversations/tasks/{task_id}/intake"
    legacy = f"/api/v1/cases/{task_id}/intake"

    paths = client.app.openapi()["paths"]
    assert canonical in paths
    assert legacy not in paths
    assert client.get(canonical).status_code == 401
    assert client.get(canonical, headers=stranger).status_code == 404
    assert client.get(canonical, headers=owner).status_code == 200
    # Compatibility remains runtime-only until all internal clients are migrated.
    assert client.get(legacy, headers=owner).status_code == 200
