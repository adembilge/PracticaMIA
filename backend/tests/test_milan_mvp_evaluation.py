"""Bilingual Milan acceptance cases with local scope and provider-failure fixtures."""
import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from app.cases import checklist_service
from app.knowledge import assistant_router
from app.knowledge.search import EvidencePassage
from test_assistant_preview import assistant_client, case_id, post  # noqa: F401
from test_case_checklist import FACTS, confirmed_intake, create_case, fake_resolver

FIXTURE = Path(__file__).resolve().parents[2] / "evals/fixtures/milan_mvp_bilingual.json"
CASES = {
    case["id"]: case
    for case in json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]
}
TIMESTAMP = datetime(2026, 11, 14, tzinfo=timezone.utc)
PASSAGE_CONTENT = {
    "0000": "Comunicare all'Ufficio Anagrafe entro 20 giorni dalla data di trasferimento.",
    "0015": "seleziona il punto 2 per questo esempio sintetico di locazione registrata",
}


@pytest.mark.parametrize("item", ["MIL-08", "MIL-09", "MIL-10", "MIL-11"])
def test_scope_matrix(client, auth_headers, monkeypatch, item):
    assert set(CASES[item]["queries"]) == {"en", "it"}
    monkeypatch.setattr(
        checklist_service, "resolve_approved_passage",
        lambda db, *, citation_id, **_: fake_resolver(citation_id),
    )
    headers = auth_headers()

    if item in {"MIL-10", "MIL-11"}:
        cid = create_case(client, headers, scoped=False)
        scope = ["yes", "yes", "no"] if item == "MIL-10" else ["yes", "no"]
        reply = client.patch(
            f"/api/v1/conversations/tasks/{cid}/scope", json={"answers": scope}, headers=headers,
        )
        assert reply.status_code == 200
        assert reply.json()["status"] == "unsupported"
    else:
        cid = create_case(client, headers)
        if item == "MIL-08":
            confirmed_intake(client, headers, cid)
            state = client.get(f"/api/v1/conversations/tasks/{cid}/workflow", headers=headers).json()
            assert state["checklist"]["total"] == 5
            assert state["official_submission"] is False
            return
        draft = client.put(
            f"/api/v1/conversations/tasks/{cid}/intake", headers=headers,
            json={"facts": {**FACTS, "housing_basis": "unknown"}, "confirm": False},
        )
        assert draft.status_code == 200
        assert draft.json()["missing_fields"] == ["housing_basis"]
    assert client.get(f"/api/v1/conversations/tasks/{cid}/package/pdf", headers=headers).status_code == 409


def resolve_topic_passage(db, *, citation_id, **kwargs):
    version, ordinal = citation_id.split(":")
    reviewed = fake_resolver(citation_id)
    return EvidencePassage(
        citation_id=citation_id, passage_id=citation_id, source_id=reviewed.source_id,
        source_version_id=version, source_revision=1, institution=reviewed.institution,
        title=reviewed.title, official_url=reviewed.official_url,
        jurisdiction=assistant_router.JURISDICTION, procedure_id=assistant_router.PROCEDURE,
        language="it", section_path="Synthetic fixture", content=PASSAGE_CONTENT[ordinal],
        passage_sha256="a" * 64, source_sha256="b" * 64,
        reviewed_at=TIMESTAMP, retrieved_at=TIMESTAMP,
    )


@pytest.mark.parametrize("language", ["en", "it"])
@pytest.mark.parametrize(("item", "expected_status"), [
    ("MIL-12", "insufficient_evidence"), ("MIL-13", "unverified_answer"),
    ("MIL-14", "generation_unavailable"),
])
def test_assistant_failure_matrix(
    assistant_client, auth_headers, monkeypatch, item, expected_status, language,
):
    resolver = (lambda *args, **kwargs: None) if item == "MIL-12" else resolve_topic_passage
    monkeypatch.setattr(assistant_router, "resolve_approved_passage", resolver)
    calls = []

    def model(_prompt):
        calls.append(True)
        if item == "MIL-14":
            raise TimeoutError("private provider diagnostic")
        return AIMessage(content='[wrong-citation] "An invented statement without evidence."')

    assistant_client.app.state.assistant_model_factory = lambda: RunnableLambda(model)
    headers = auth_headers()
    cid = case_id(assistant_client, headers)
    response = post(
        assistant_client, cid, headers, question=CASES[item]["queries"][language], language=language,
    )
    assert response.status_code == 200
    assert response.json()["status"] == expected_status
    assert response.json()["answer"] is None
    assert "private provider diagnostic" not in response.text
    assert len(calls) == (0 if item == "MIL-12" else 1)
    if item == "MIL-12":
        assert response.json()["sources"] == []
    if item == "MIL-14":
        assert assistant_client.get(f"/api/v1/conversations/tasks/{cid}/workflow", headers=headers).status_code == 200


@pytest.mark.parametrize(("selection", "expected_status"), [
    ("1", "answer_generated"), ("0", "insufficient_evidence"),
    ("2", "unverified_answer"), ("1\nextra text", "unverified_answer"),
])
def test_reviewed_quote_selection(
    assistant_client, auth_headers, monkeypatch, selection, expected_status,
):
    def resolve(db, *, citation_id, **kwargs):
        passage = resolve_topic_passage(db, citation_id=citation_id, **kwargs)
        return replace(passage, content=passage.content + " Unrelated fixture text.")

    monkeypatch.setattr(assistant_router, "resolve_approved_passage", resolve)
    assistant_client.app.state.assistant_model_factory = lambda: RunnableLambda(
        lambda _: AIMessage(content=selection),
    )
    headers = auth_headers()
    cid = case_id(assistant_client, headers)
    response = post(
        assistant_client, cid, headers, question="How many days do I have to report a Milan address change?", language="en",
    ).json()
    assert response["status"] == expected_status
    if selection == "1":
        assert PASSAGE_CONTENT["0000"] in response["answer"]
        assert response["sources"][0]["excerpt"] == PASSAGE_CONTENT["0000"]
    else:
        assert response["answer"] is None


@pytest.mark.parametrize("language", ["en", "it"])
@pytest.mark.parametrize("approved", [True, False])
def test_product_submission_handoff_uses_only_current_reviewed_evidence(
    assistant_client, auth_headers, monkeypatch, language, approved,
):
    def resolve(db, *, citation_id, **kwargs):
        if not approved:
            return None
        assert citation_id == CASES["MIL-06"]["passage_candidates"][0]
        return EvidencePassage(
            citation_id=citation_id, passage_id=citation_id, source_id="synthetic",
            source_version_id=citation_id.split(":")[0], source_revision=1,
            institution="Synthetic fixture", title="Synthetic ANPR fixture",
            official_url="https://example.invalid", jurisdiction=assistant_router.JURISDICTION,
            procedure_id=assistant_router.PROCEDURE, language="it", section_path="Riepilogo",
            content='Verifica la correttezza dei dati della dichiarazione; '
                    'Seleziona il tasto “Invio dichiarazione”.',
            passage_sha256="a" * 64, source_sha256="b" * 64,
            reviewed_at=TIMESTAMP, retrieved_at=TIMESTAMP,
        )

    def unexpected_model():
        pytest.fail("The fixed product handoff must not call the model")

    monkeypatch.setattr(assistant_router, "resolve_approved_passage", resolve)
    assistant_client.app.state.assistant_model_factory = unexpected_model
    headers = auth_headers()
    cid = case_id(assistant_client, headers)
    answer = post(
        assistant_client, cid, headers, question=CASES["MIL-06"]["queries"][language],
        language=language,
    ).json()
    if approved:
        assert answer["status"] == "answer_generated"
        assert "Invio dichiarazione" in answer["answer"]
        assert len(answer["sources"]) == 1
    else:
        assert answer["status"] == "insufficient_evidence"
        assert answer["answer"] is None
        assert answer["sources"] == []


@pytest.mark.parametrize("language", ["en", "it"])
@pytest.mark.parametrize("item", [f"MIL-{index:02}" for index in range(1, 8)])
def test_bilingual_assistant_matrix(
    assistant_client, auth_headers, monkeypatch, item, language,
):
    # Minimal synthetic passage texts exercise exact-quotation and routing
    # contracts. Live source integrity and provider quality are evaluated in Preview.
    lines = {
        "0000": PASSAGE_CONTENT["0000"],
        "0005": "Inoltre, è necessario dichiarare la nuova situazione abitativa ai fini Tari.",
        "0015": PASSAGE_CONTENT["0015"],
        "0017": "Per agevolare gli accertamenti (contratto e assenso del proprietario).",
        "0018": "Gli allegati non sono obbligatori",
        "0021": "Verifica la correttezza dei dati della dichiarazione; "
                "Seleziona il tasto “Invio dichiarazione”.",
    }

    def resolve(db, *, citation_id, **kwargs):
        sample = resolve_topic_passage(
            db, citation_id=CASES["MIL-01"]["passage_candidates"][0], **kwargs,
        )
        version, ordinal = citation_id.split(":")
        reviewed = fake_resolver(citation_id)
        return replace(
            sample, citation_id=citation_id, passage_id=citation_id,
            source_id=reviewed.source_id, source_version_id=version,
            official_url=reviewed.official_url, content=lines[ordinal],
        )

    def no_model():
        pytest.fail("Reviewed exact prompts and deferrals must not call the model")

    monkeypatch.setattr(assistant_router, "resolve_approved_passage", resolve)
    assistant_client.app.state.assistant_model_factory = no_model
    headers = auth_headers()
    cid = case_id(assistant_client, headers)
    fixture = CASES[item]
    response = post(
        assistant_client, cid, headers,
        question=fixture["queries"][language], language=language,
    )
    assert response.status_code == 200
    answer = response.json()
    if fixture["expected_kind"] == "abstain":
        assert answer["status"] == "insufficient_evidence"
        assert answer["answer"] is None and answer["sources"] == []
    else:
        assert answer["status"] == "answer_generated"
        sources = {entry["citation_id"]: entry["excerpt"] for entry in answer["sources"]}
        assert sources and set(sources) <= set(fixture["passage_candidates"])
        assert assistant_router.verify_exact_quotations(answer["answer"], sources)
