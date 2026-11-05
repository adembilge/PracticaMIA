"""Independent, deterministic hostile-input campaign against real FastAPI routes.

Runs with valid locally signed JWTs but no external user or identity provider.
It tests 150+ adverse combinations, not just the happy path; all names, IDs,
addresses and documents here are invented test-only values.
"""
from itertools import product
from uuid import uuid4

import pytest

from app.cases.scope import classify_scope

SCOPE_PATH = "/api/v1/cases"
CANDIDATES = ["yes", "no", "unsure"]


def test_case_scope_all_243_combinations_match_prefix_state_machine():
    expected = ("yes", "yes", "yes", "no", "yes")
    for values in product(CANDIDATES, repeat=5):
        status = "provisionally_in_scope"
        for received, correct in zip(values, expected, strict=True):
            if received == "unsure":
                status = "needs_information"
                break
            if received != correct:
                status = "unsupported"
                break
        assert classify_scope(list(values)) == status
    assert classify_scope([]) == "incomplete"
    assert classify_scope(["yes", "yes"]) == "incomplete"


def test_cross_tenant_access_campaign_is_indistinguishable_from_missing(
    client, auth_headers,
):
    alice = auth_headers("alice")
    bob = auth_headers("bob")
    created = []
    for index in range(8):
        owner = alice if index % 2 == 0 else bob
        answer = client.post(SCOPE_PATH, headers=owner, json={})
        assert answer.status_code == 201, answer.text
        created.append((answer.json()["id"], owner, bob if owner is alice else alice))
    for case_id, owner, stranger in created:
        for method, suffix, body in [
            ("GET", "", None),
            ("PATCH", "/scope", {"answers": ["no"]}),
            ("DELETE", "", None),
        ]:
            response = client.request(
                method, SCOPE_PATH + "/" + case_id + suffix,
                headers=stranger, json=body,
            )
            assert response.status_code == 404, (method, case_id, response.text)
            # The same owner always retains the record even after the attack.
            current = client.get(SCOPE_PATH + "/" + case_id, headers=owner)
            assert current.status_code == 200
            assert current.json()["scope_answers"] == []
    assert len(client.get(SCOPE_PATH, headers=alice).json()) == 4
    assert len(client.get(SCOPE_PATH, headers=bob).json()) == 4
    for case_id, owner, _ in created:
        assert client.delete(SCOPE_PATH + "/" + case_id, headers=owner).status_code == 204


def test_all_untrusted_case_write_fields_and_type_confusion_fail_closed(
    client, auth_headers,
):
    owner = auth_headers("alice")
    case_id = client.post(SCOPE_PATH, headers=owner, json={}).json()["id"]
    forbidden = [
        {"answers": ["yes"], "owner_subject": "bob"},
        {"answers": ["yes"], "status": "provisionally_in_scope"},
        {"answers": ["yes"], "procedure": "malicious"},
        {"answers": ["YES"]},
        {"answers": [True]},
        {"answers": [None]},
        {"answers": [1]},
        {"answers": ["yes"] * 6},
        {"answers": []},
        {"answers": "yes"},
        {"answers": ["yes", "not-sure"]},
        {"answers": [{"key": "yes"}]},
        {"answers": ["yes"], "source_version_id": str(uuid4())},
        {"answers": ["yes"], "approved": True},
        {"answers": ["yes"], "submission_status": "officially_confirmed"},
        {"answers": ["yes"], "agency_reference": "fake-number"},
    ]
    for i, payload in enumerate(forbidden):
        response = client.patch(
            SCOPE_PATH + "/" + case_id + "/scope",
            headers=owner, json=payload,
        )
        assert response.status_code == 422, (i, response.text)
        recorded = client.get(SCOPE_PATH + "/" + case_id, headers=owner).json()
        assert recorded["status"] == "draft"
        assert recorded["scope_answers"] == []

    for payload in [
        {"owner_subject": "bob"},
        {"status": "officially_confirmed"},
        {"procedure": "italian-citizenship"},
        {"scope_answers": ["yes"]},
        {"is_admin": True},
    ]:
        assert client.post(SCOPE_PATH, headers=owner, json=payload).status_code == 422


@pytest.mark.parametrize("unsafe_value", [
    "__proto__", "' OR 1=1 --", "<script>alert(1)</script>",
    "\x00", "../../../etc/passwd", "%2F%2E%2E%2F",
    "a" * 512, "s" * 64,
])
def test_path_object_and_injection_strings_never_expose_case_details(
    client, auth_headers, unsafe_value,
):
    owner = auth_headers("alice")
    response = client.get(SCOPE_PATH + "/" + unsafe_value, headers=owner)
    assert response.status_code in (404, 422), response.text
    assert "owner_subject" not in response.text


def test_anonymous_api_campaign_never_discloses_user_cases(
    client, auth_headers,
):
    owner = auth_headers("alice")
    case_id = client.post(SCOPE_PATH, json={}, headers=owner).json()["id"]
    for headers in [{}, {"Authorization": "Bearer none"},
                    {"X-User-Id": "alice"}, {"Authorization": "Basic Zm9vOmJhcg=="}]:
        for route in [SCOPE_PATH, SCOPE_PATH + "/" + case_id]:
            response = client.get(route, headers=headers)
            assert response.status_code == 401, response.text
            assert case_id not in response.text
