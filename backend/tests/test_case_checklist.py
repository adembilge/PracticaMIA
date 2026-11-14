"""Read-only first-route checklist: signed evidence, owner access and revocation.

Synthetic evidence resolution is injected; no live municipality requests or LLM.
The real resolver's snapshot and audit-event validation is covered separately.
"""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from app.cases import checklist_service as svc
from app.rules.approval import has_valid_human_review_signature
from app.rules.engine import load_catalog

SCOPE = ["yes", "yes", "yes", "no", "yes"]
FACTS = {
    "citizenship_class": "italian",
    "registration_context": "already_registered_in_italy",
    "destination_municipality": "milano",
    "household_scope": "individual_no_aggregation",
    "housing_basis": "registered_private_rental",
}
FIRST = "/api/v1/cases"


def create_case(client, headers, *, scoped=True):
    created = client.post(FIRST, json={}, headers=headers)
    assert created.status_code == 201, created.text
    case_id = created.json()["id"]
    if scoped:
        result = client.patch(
            f"{FIRST}/{case_id}/scope", json={"answers": SCOPE}, headers=headers
        )
        assert result.status_code == 200, result.text
    return case_id


def confirmed_intake(client, headers, case_id, *, facts=FACTS):
    result = client.put(
        f"{FIRST}/{case_id}/intake",
        json={"facts": facts, "confirm": True}, headers=headers,
    )
    assert result.status_code == 200, result.text


def fake_resolver(ref, *, dropped=None, wrong_url=False):
    if ref == dropped:
        return None
    source_id = next((src for src, details in svc.PINNED_SOURCE_VERSIONS.items()
                      if ref.startswith(details[0] + ":")), None)
    if source_id is None:
        return None
    version, url, _ = svc.PINNED_SOURCE_VERSIONS[source_id]
    return SimpleNamespace(
        citation_id=ref,
        source_id=source_id,
        source_version_id=version,
        official_url=("https://untrusted.example.test/rules" if wrong_url else url),
        institution="Test reviewed source",
        title="Synthetic reviewed source",
        reviewed_at=datetime(2026, 11, 8, tzinfo=timezone.utc),
        retrieved_at=datetime(2026, 11, 7, tzinfo=timezone.utc),
    )


def test_checklist_read_requires_owner_and_current_confirmed_intake(client, auth_headers, monkeypatch):
    alice, bob = auth_headers("alice"), auth_headers("bob")
    case_id = create_case(client, alice, scoped=False)
    path = f"{FIRST}/{case_id}/checklist"
    assert client.get(path).status_code == 401
    assert client.get(path, headers=bob).status_code == 404

    empty = client.get(path, headers=alice)
    assert empty.status_code == 200
    assert empty.json()["status"] == "needs_scope"
    assert empty.json()["items"] == []
    assert empty.headers["cache-control"] == "private, no-store"

    assert client.patch(f"{FIRST}/{case_id}/scope",
                        json={"answers": SCOPE}, headers=alice).status_code == 200
    missing = client.get(path, headers=alice).json()
    assert missing["status"] == "needs_confirmation"
    assert missing["items"] == []

    assert client.put(f"{FIRST}/{case_id}/intake",
                      json={"facts": {"citizenship_class": "italian"}, "confirm": False},
                      headers=alice).status_code == 200
    assert client.get(path, headers=alice).json()["status"] == "needs_confirmation"

    calls = []
    def approved(_db, *, citation_id, **_kwargs):
        calls.append(citation_id)
        return fake_resolver(citation_id)
    monkeypatch.setattr(svc, "resolve_approved_passage", approved)
    confirmed_intake(client, alice, case_id)
    response = client.get(path, headers=alice)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "ready_for_user_review"
    assert len(data["items"]) == 5
    assert len(set(calls)) == 11
    assert data["synthetic_only"] is True
    assert data["verified_evidence"] is True
    assert data["eligibility_evaluated"] is False
    assert data["documents_verified"] is False
    assert data["government_submitted"] is False
    assert data["required_document_types"] == []
    assert data["ruleset_version"] == svc._reviewed_catalog()["version"]
    assert all(item["status"] == "needs_user" and item["evidence"]
               for item in data["items"])
    assert any(c["archived_reference"] for item in data["items"]
               for c in item["evidence"])
    assert "facts" not in data and "scope_answers" not in data
    assert case_id not in str(data)
    assert "owner_subject" not in str(data)
    assert client.get(path, headers=bob).status_code == 404

    # Changing the scope deletes the confirmed intake and any trusted output.
    changed = client.patch(f"{FIRST}/{case_id}/scope",
                           json={"answers": ["no"]}, headers=alice)
    assert changed.status_code == 200
    invalidated = client.get(path, headers=alice).json()
    assert invalidated["status"] == "needs_scope"
    assert invalidated["items"] == []


def test_outside_first_route_produces_no_administrative_checklist(client, auth_headers, monkeypatch):
    alice = auth_headers("alice")
    case_id = create_case(client, alice)
    confirmed_intake(client, alice, case_id, facts={**FACTS, "housing_basis": "guest"})
    def must_not_call(*_args, **_kwargs):
        raise AssertionError("No source access for unsupported route")
    monkeypatch.setattr(svc, "resolve_approved_passage", must_not_call)
    r = client.get(f"{FIRST}/{case_id}/checklist", headers=alice)
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "outside_first_route"
    assert d["items"] == []
    assert d["eligibility_evaluated"] is False


def test_revoked_citation_or_url_substitution_fails_closed(client, auth_headers, monkeypatch):
    alice = auth_headers("alice")
    case_id = create_case(client, alice)
    confirmed_intake(client, alice, case_id)
    target = svc._reviewed_catalog()["rules"][0]["evidence_refs"][0]
    path = f"{FIRST}/{case_id}/checklist"

    monkeypatch.setattr(
        svc, "resolve_approved_passage",
        lambda _db, *, citation_id, **_: fake_resolver(citation_id, dropped=target)
    )
    denied = client.get(path, headers=alice).json()
    assert denied["status"] == "evidence_unavailable"
    assert denied["items"] == []

    monkeypatch.setattr(
        svc, "resolve_approved_passage",
        lambda _db, *, citation_id, **_: fake_resolver(citation_id, wrong_url=True)
    )
    denied = client.get(path, headers=alice).json()
    assert denied["status"] == "evidence_unavailable"
    assert denied["items"] == []


def test_review_signature_is_pinned_to_existing_approved_catalog(monkeypatch, client, auth_headers):
    key_path = Path(__file__).resolve().parents[2] / (
        "requirements/milan-residence-change/review_public_key_v1.b64"
    )
    assert key_path.read_text(encoding="utf-8").strip() == svc.PINNED_FIRST_ROUTE_PUBLIC_KEY
    signed = load_catalog(svc.CATALOG_PATH.read_text(encoding="utf-8"))
    assert has_valid_human_review_signature(signed, svc.PINNED_FIRST_ROUTE_PUBLIC_KEY)
    changed = deepcopy(signed)
    changed["rules"][0]["result"]["route"] = "another_route"
    assert not has_valid_human_review_signature(changed, svc.PINNED_FIRST_ROUTE_PUBLIC_KEY)

    alice = auth_headers("alice")
    case_id = create_case(client, alice)
    confirmed_intake(client, alice, case_id)
    # A catalog with an invalid signature cannot issue even partially supported steps.
    monkeypatch.setattr(svc, "_reviewed_catalog",
                        lambda: {**changed, "status": "pending_review"})
    r = client.get(f"{FIRST}/{case_id}/checklist", headers=alice)
    assert r.status_code == 200
    assert r.json()["status"] == "evidence_unavailable"
    assert r.json()["items"] == []
