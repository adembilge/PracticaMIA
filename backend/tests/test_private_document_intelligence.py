"""Synthetic-only authenticated vault intelligence: extract, correct, compare, expire.

No real identity files. Test scanner uses a stub; production still fails closed
on unavailable scanner, privacy review, missing key or purge configuration.
"""
from datetime import datetime, timedelta, timezone
from io import BytesIO
import json

from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas
from sqlalchemy import select

from app.private_documents.model import PrivateCaseDocument
from app.private_documents import intelligence as intel
from app.private_documents import intelligence_router as route
from app.private_documents.security import open_bytes
from test_private_documents import document_client  # noqa: F401 - fixture
from app.preparation.extract import DocumentRejected

SCOPE=["yes","yes","yes","no","yes"]
FACTS={
    "citizenship_class":"italian",
    "registration_context":"already_registered_in_italy",
    "destination_municipality":"milano",
    "household_scope":"individual_no_aggregation",
    "housing_basis":"registered_private_rental",
    "move_in_date":"2026-11-05",
}


def sample_pdf(*lines):
    stream=BytesIO()
    document=canvas.Canvas(stream)
    for i,line in enumerate(lines):
        document.drawString(35,750-i*18,line)
    document.save()
    return stream.getvalue()


def prepare_case(client, headers):
    case_id=client.post("/api/v1/cases",json={},headers=headers).json()["id"]
    response=client.patch(f"/api/v1/cases/{case_id}/scope",
                          json={"answers":SCOPE},headers=headers)
    assert response.status_code==200
    response=client.put(f"/api/v1/cases/{case_id}/intake",
                        json={"facts":FACTS,"confirm":True},headers=headers)
    assert response.status_code==200,response.text
    return case_id


def upload(client, headers, case_id, body,category="housing_document"):
    response=client.post(
        f"/api/v1/cases/{case_id}/private-documents",
        headers=headers,
        data={
            "category":category,"privacy_ack":"true",
            "consent_version":"private-documents-2026-11-v1",
        },
        files={"file":("fictional.pdf",body,"application/pdf")},
    )
    assert response.status_code==201,response.text
    return response.json()["id"]


def review_payload(result, *, corrected=None):
    return {
        "extraction_digest":result["extraction_digest"],
        "confirm":True,
        "selections":[{
            "field_name":candidate["field_name"],
            "candidate_id":candidate["candidate_id"],
            "confirmed_value":(corrected or {}).get(
                candidate["field_name"],candidate["suggested_value"]
            ),
        } for candidate in result["candidates"]],
    }


def test_private_housing_extraction_review_comparison_and_isolation(
    document_client,auth_headers,
):
    client=document_client
    alice,bob=auth_headers("alice"),auth_headers("bob")
    case_id=prepare_case(client,alice)
    source=sample_pdf(
        "Housing arrangement: Registered private rental agreement",
        "Move-in date: 2026-11-05",
        "Property address: Fictional Via 77 (must never be extracted)",
    )
    doc_id=upload(client,alice,case_id,source)
    base=f"/api/v1/cases/{case_id}/private-documents/{doc_id}/intelligence"
    assert client.get(base).status_code==401
    assert client.get(base,headers=bob).status_code==404
    assert client.post(base+"/extract",headers=bob).status_code==404
    # Give a structurally valid payload so FastAPI reaches owner authorization.
    assert client.put(base+"/review",headers=bob,json={
        "extraction_digest":"a"*64,"confirm":True,
        "selections":[{"field_name":"move_in_date","candidate_id":"b"*64,
                       "confirmed_value":"2026-11-05"}],
    }).status_code==404

    initial=client.get(base,headers=alice)
    assert initial.status_code==200
    assert initial.headers["cache-control"]=="private, no-store"
    assert initial.json()["status"]=="needs_extraction"
    generated=client.post(base+"/extract",headers=alice)
    assert generated.status_code==200,generated.text
    result=generated.json()
    assert result["status"]=="needs_user_confirmation"
    assert {c["field_name"] for c in result["candidates"]}=={
        "housing_basis","move_in_date"
    }
    assert len(result["candidates"])==2
    assert result["no_legal_verification"] is True
    assert result["official_submission"] is False
    assert "Property address" not in generated.text
    assert "Fictional Via" not in generated.text
    assert len(result["extraction_digest"])==64

    with client.app.state.session_factory() as db:
        row=db.get(PrivateCaseDocument,doc_id)
        assert row.review_ciphertext
        assert b"registered_private_rental" not in row.review_ciphertext
        plaintext=open_bytes(
            row.review_ciphertext,
            key=client.app.state.private_document_key,case_id=case_id,
            owner="alice",document_id=doc_id+":review",
        )
        assert b"Fictional Via" not in plaintext
        assert b"Property address" not in plaintext
        assert b"full_page_text" not in plaintext
        data=json.loads(plaintext)
        assert "pages" not in data

    no_ack=review_payload(result)
    no_ack["confirm"]=False
    assert client.put(base+"/review",json=no_ack,headers=alice).status_code==422

    fake=review_payload(result)
    fake["selections"][0]["candidate_id"]="0"*64
    assert client.put(base+"/review",json=fake,headers=alice).status_code==409
    stale=review_payload(result)
    stale["extraction_digest"]="0"*64
    assert client.put(base+"/review",json=stale,headers=alice).status_code==409

    correction=review_payload(result,corrected={"housing_basis":"guest"})
    saved=client.put(base+"/review",json=correction,headers=alice)
    assert saved.status_code==200,saved.text
    result=saved.json()
    assert result["status"]=="conflict"
    assert result["user_reviewed"] is True
    assert len(result["comparisons"])==2
    assert any(x["field_name"]=="housing_basis" and
               x["comparison"]=="conflict" for x in result["comparisons"])
    assert any(x["field_name"]=="move_in_date" and
               x["comparison"]=="match" for x in result["comparisons"])

    # Reviewing a document cannot silently replace confirmed case facts.
    intake=client.get(f"/api/v1/cases/{case_id}/intake",headers=alice).json()
    assert intake["facts"]==FACTS
    assert intake["confirmed"] is True

    # Saved review survives an owner reload and is no more valid after intake edit.
    assert client.get(base,headers=alice).json()["status"]=="conflict"
    assert client.put(f"/api/v1/cases/{case_id}/intake",
                      json={"facts":FACTS,"confirm":False},headers=alice).status_code==200
    missing=client.get(base,headers=alice).json()
    assert missing["status"]=="needs_confirmed_intake"
    assert all(c["comparison"]=="no_confirmed_case_fact"
               for c in missing["comparisons"])

    assert client.delete(f"/api/v1/cases/{case_id}/private-documents/{doc_id}",
                         headers=alice).status_code==204
    assert client.get(base,headers=alice).status_code==404


def test_extraction_is_idempotent_without_duplicate_ocr(
    document_client,auth_headers,monkeypatch,
):
    client=document_client
    alice=auth_headers("alice")
    case_id=prepare_case(client,alice)
    doc_id=upload(client,alice,case_id,sample_pdf("Move-in date: 2026-11-05"))
    url=f"/api/v1/cases/{case_id}/private-documents/{doc_id}/intelligence/extract"
    calls=[]
    original=route.intel.new_review
    def tracked(*args,**kwargs):
        calls.append(1)
        return original(*args,**kwargs)
    monkeypatch.setattr(route.intel,"new_review",tracked)
    assert client.post(url,headers=alice).status_code==200
    assert client.post(url,headers=alice).status_code==200
    assert len(calls)==1


def test_missing_fields_ambiguity_and_unsupported_categories(
    document_client,auth_headers,
):
    client=document_client
    alice=auth_headers("alice")
    case_id=prepare_case(client,alice)
    unknown=upload(client,alice,case_id,sample_pdf("No supported label: fictional"))
    base=f"/api/v1/cases/{case_id}/private-documents/{unknown}/intelligence"
    assert client.post(base+"/extract",headers=alice).json()["status"]=="no_supported_fields"
    assert client.put(base+"/review",headers=alice,json={
        "extraction_digest":"a"*64,"confirm":True,
        "selections":[{"field_name":"move_in_date","candidate_id":"b"*64,
                       "confirmed_value":"2026-11-05"}],
    }).status_code==409
    identity=upload(client,alice,case_id,sample_pdf("Fake identity only"),"identity_document")
    route_id=f"/api/v1/cases/{case_id}/private-documents/{identity}/intelligence"
    assert client.post(route_id+"/extract",headers=alice).status_code==422
    assert client.get(route_id,headers=alice).json()["status"]=="unsupported_category"

    document=upload(client,alice,case_id,sample_pdf(
        "Housing basis: Owner",
        "Housing basis: Guest",
    ))
    base=f"/api/v1/cases/{case_id}/private-documents/{document}/intelligence"
    extracted=client.post(base+"/extract",headers=alice).json()
    assert extracted["ambiguous_fields"]==["housing_basis"]
    chosen={
        "extraction_digest":extracted["extraction_digest"],"confirm":True,
        "selections":[{
            "field_name":"housing_basis",
            "candidate_id":extracted["candidates"][0]["candidate_id"],
            "confirmed_value":"owner",
        }],
    }
    assert client.put(base+"/review",headers=alice,json=chosen).json()["status"]=="needs_manual_review"


def test_expiration_and_ciphertext_integrity_fail_closed(
    document_client,auth_headers,
):
    client=document_client
    alice=auth_headers("alice")
    case_id=prepare_case(client,alice)
    doc_id=upload(client,alice,case_id,sample_pdf("Move-in date: 2026-11-05"))
    base=f"/api/v1/cases/{case_id}/private-documents/{doc_id}/intelligence"
    with client.app.state.session_factory() as db:
        row=db.get(PrivateCaseDocument,doc_id)
        row.ciphertext=b"corrupted"+row.ciphertext
        db.commit()
    assert client.post(base+"/extract",headers=alice).status_code==503
    with client.app.state.session_factory() as db:
        row=db.get(PrivateCaseDocument,doc_id)
        row.expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)
        db.commit()
    assert client.get(base,headers=alice).status_code==404
    assert client.post(base+"/extract",headers=alice).status_code==404
