"""Unified case workflow with owner-only, evidence-bound user review marks."""
from datetime import datetime, timezone
from types import SimpleNamespace

from app.cases import checklist_service as svc
from test_case_checklist import create_case, confirmed_intake, FACTS, SCOPE

ROOT="/api/v1/cases"


def evidence(ref, reviewed="2026-11-08"):
    source = next(
        name for name, (version, _url, _archived) in
        svc.PINNED_SOURCE_VERSIONS.items() if ref.startswith(version + ":")
    )
    version, url, _ = svc.PINNED_SOURCE_VERSIONS[source]
    return SimpleNamespace(
        citation_id=ref, source_id=source, source_version_id=version,
        official_url=url, title="Reviewed fictional source fixture",
        institution="Synthetic test", retrieved_at=datetime(
            2026, 11, 7, tzinfo=timezone.utc
        ), reviewed_at=datetime.fromisoformat(reviewed).replace(tzinfo=timezone.utc),
    )


def test_unified_case_journey_and_owner_scoped_progress(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        svc, "resolve_approved_passage",
        lambda _db, *, citation_id, **_: evidence(citation_id),
    )
    alice, bob = auth_headers("alice"), auth_headers("bob")
    case_id = create_case(client, alice, scoped=False)
    path=f"{ROOT}/{case_id}/workflow"
    write=path+"/checklist"
    assert client.get(path).status_code == 401
    assert client.get(path, headers=bob).status_code == 404
    initial=client.get(path, headers=alice)
    assert initial.status_code == 200
    assert initial.headers["cache-control"] == "private, no-store"
    assert initial.json()["next_action"] == "answer_scope"
    assert initial.json()["checklist"]["fingerprint"] is None
    assert initial.json()["official_submission"] is False

    assert client.patch(
        f"{ROOT}/{case_id}/scope",json={"answers":SCOPE},headers=alice,
    ).status_code == 200
    assert client.get(path, headers=alice).json()["next_action"] == "confirm_intake"
    confirmed_intake(client, alice, case_id)
    state=client.get(path, headers=alice).json()
    checklist=state["checklist"]
    assert state["next_action"] == "review_checklist"
    assert [s["id"] for s in state["steps"]] == [
        "scope","intake","guidance","checklist","documents","package","handoff"
    ]
    assert len(checklist["items"]) == 5
    assert len(checklist["fingerprint"]) == 64
    assert state["package"]["download_allowed"] is True
    assert state["documents"]["enabled"] is False
    assert checklist["reviewed_count"] == 0
    assert state["eligibility_evaluated"] is False
    assert state["official_submission"] is False

    item_id=checklist["items"][0]["id"]
    mark={"item_id":item_id,"reviewed":True,
          "fingerprint":checklist["fingerprint"]}
    assert client.patch(write,json=mark,headers=bob).status_code == 404
    assert client.patch(write,json=mark).status_code == 401
    assert client.patch(write,json={**mark,"applicant_name":"secret"},
                        headers=alice).status_code == 422
    assert client.patch(write,json={**mark,"item_id":"invented_proof"},
                        headers=alice).status_code == 409
    assert client.patch(write,json={**mark,"fingerprint":"a"*64},
                        headers=alice).status_code == 409

    reviewed=client.patch(write,json=mark,headers=alice)
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.headers["cache-control"] == "private, no-store"
    assert reviewed.json()["checklist"]["reviewed_count"] == 1
    assert reviewed.json()["next_action"] == "review_checklist"
    assert reviewed.json()["official_submission"] is False
    assert item_id in reviewed.json()["checklist"]["reviewed_items"]
    assert client.get(path,headers=alice).json()["checklist"]["reviewed_count"] == 1
    assert client.get(path,headers=bob).status_code == 404

    # Marking a review does not declare a legal action complete or change the PDF.
    assert client.get(f"{ROOT}/{case_id}/package",headers=alice).json()[
        "download_allowed"
    ] is True
    assert all(i["status"]=="needs_user" for i in reviewed.json()["checklist"]["items"])
    reset=client.patch(write,json={**mark,"reviewed":False},headers=alice)
    assert reset.status_code == 200
    assert reset.json()["checklist"]["reviewed_count"] == 0


def test_progress_invalidation_on_fact_edit_source_review_or_revocation(
    client, auth_headers, monkeypatch,
):
    current={"date":"2026-11-08","revoked":False}
    def lookup(_db, *, citation_id, **_):
        if current["revoked"]:
            return None
        return evidence(citation_id,current["date"])
    monkeypatch.setattr(svc,"resolve_approved_passage",lookup)
    alice=auth_headers("alice")
    case_id=create_case(client,alice)
    confirmed_intake(client,alice,case_id,facts={
        **FACTS,"move_in_date":"2026-11-05",
    })
    path=f"{ROOT}/{case_id}/workflow"
    write=path+"/checklist"
    first=client.get(path,headers=alice).json()["checklist"]
    selected=first["items"][0]["id"]
    payload={"item_id":selected,"reviewed":True,"fingerprint":first["fingerprint"]}
    assert client.patch(write,json=payload,headers=alice).status_code == 200
    assert client.get(path,headers=alice).json()["checklist"]["reviewed_count"] == 1

    current["revoked"]=True
    unavailable=client.get(path,headers=alice).json()
    assert unavailable["checklist"]["reviewed_count"] == 0
    assert unavailable["checklist"]["items"] == []
    assert unavailable["package"]["download_allowed"] is False
    assert client.patch(write,json=payload,headers=alice).status_code == 409

    current["revoked"]=False
    current["date"]="2026-11-09"
    replaced=client.get(path,headers=alice).json()
    assert replaced["checklist"]["fingerprint"] != first["fingerprint"]
    assert replaced["checklist"]["reviewed_count"] == 0
    assert client.patch(write,json=payload,headers=alice).status_code == 409

    new_payload={**payload,"fingerprint":replaced["checklist"]["fingerprint"]}
    assert client.patch(write,json=new_payload,headers=alice).status_code == 200
    assert client.get(path,headers=alice).json()["checklist"]["reviewed_count"] == 1
    assert client.put(f"{ROOT}/{case_id}/intake",headers=alice,json={
        "facts":{**FACTS,"move_in_date":"2026-11-06"},"confirm":True,
    }).status_code == 200
    changed=client.get(path,headers=alice).json()
    assert changed["checklist"]["reviewed_count"] == 0
    assert changed["checklist"]["fingerprint"] != replaced["checklist"]["fingerprint"]

    assert client.patch(f"{ROOT}/{case_id}/scope",headers=alice,
                        json={"answers":["no"]}).status_code == 200
    invalid=client.get(path,headers=alice).json()
    assert invalid["next_action"] == "answer_scope"
    assert invalid["checklist"]["items"] == []
    assert invalid["checklist"]["reviewed_items"] == {}


def test_all_five_marks_mean_read_only_and_can_be_unmarked(
    client,auth_headers,monkeypatch,
):
    monkeypatch.setattr(svc,"resolve_approved_passage",
                        lambda _db,*,citation_id,**_: evidence(citation_id))
    alice=auth_headers("alice")
    case_id=create_case(client,alice)
    confirmed_intake(client,alice,case_id)
    path=f"{ROOT}/{case_id}/workflow"
    state=client.get(path,headers=alice).json()
    fingerprint=state["checklist"]["fingerprint"]
    for item in state["checklist"]["items"]:
        mark={"item_id":item["id"],"reviewed":True,"fingerprint":fingerprint}
        r=client.patch(path+"/checklist",json=mark,headers=alice)
        assert r.status_code == 200,r.text
    final=client.get(path,headers=alice).json()
    assert final["checklist"]["reviewed_count"] == 5
    assert final["steps"][3]["status"] == "reviewed_by_user"
    assert final["next_action"] == "download_draft"
    assert final["official_submission"] is False
    assert final["package"]["download_allowed"] is True
    # The reviewed progress is not inserted into official claims.
    assert client.get(f"{ROOT}/{case_id}/package",headers=alice).json()[
        "official_acceptance"
    ] is False
