"""Exercise unreadable-notice questions through the worker and signed reconnect API."""

from functools import partial
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import sessionmaker

from app.agent.candidate_resolution import choose_candidate_step
from app.agent.checkpoints import CheckpointState, load_checkpoint
from app.agent.contract import SendMessage
from app.agent.intent_extraction import extract_intent, identify_intent_step
from app.agent.notice_clarification import unreadable_notice_field
from app.agent.reconnect_router import build_reconnect_router
from app.agent.run_requests import StoredMessage, accept_message
from app.agent.threads import create_thread, link_case_to_thread
from app.agent.worker import run_worker_step
from test_agent_reconnect_http import KEY, OWNER, run_url


@pytest.mark.parametrize(("language", "opening", "field", "prompt", "hint", "reply"), [
    ("en", "My appointment notice arrived. The date is unreadable. When should I go?",
     "appointment_date", "line with the appointment date", "Remove names, identifiers",
     {"text": "Appointment date could be 16/12/2026 (fixture excerpt)"}),
    ("it", "Non riesco a leggere la data sulla lettera di convocazione. Quando devo andare?",
     "appointment_date", "riga con la data dell’appuntamento", "Oscura nomi, identificativi",
     {"disposition": "unknown"}),
    ("en", "A letter requests an attachment. The copy cuts off the name. Which file is needed?",
     "attachment_name", "line that names the requested attachment", "Remove names, identifiers",
     {"disposition": "skip"}),
    ("it", "Non riesco a leggere quale allegato chiede la comunicazione. Quale file devo inviare?",
     "attachment_name", "riga con il nome dell’allegato richiesto", "Oscura nomi, identificativi",
     {"text": "Nome allegato forse documento sintetico"}),
])
def test_notice_question_reconnects_and_keeps_the_reply_unverified(
    client, auth_headers, language, opening, field, prompt, hint, reply,
):
    headers = auth_headers()
    created = client.post("/api/v1/cases", headers=headers, json={})
    assert created.status_code == 201
    case_id = UUID(created.json()["id"])
    sessions = client.app.state.session_factory
    with sessions.begin() as db:
        thread_id = create_thread(db, principal=OWNER)
        assert link_case_to_thread(db, principal=OWNER, thread_id=thread_id, case_id=case_id)
        accepted = accept_message(
            db, thread_id=thread_id, principal=OWNER, key=KEY,
            message=SendMessage(client_message_id=uuid4(), case_id=case_id, text=opening, language=language),
        )
    context = {"thread_id": thread_id, "run_id": accepted.run_id, "principal": OWNER, "key": KEY}
    choose_candidate = partial(
        choose_candidate_step, case_locations={}, confirmed_dates={}, confirmed_circumstances={},
        assignments=(), trusted_passage_ids=frozenset(), reviewed_labels={},
    )
    run_worker_step(sessions, **context, execute=lambda *_: CheckpointState(next_node="identify_intent"))
    run_worker_step(sessions, **context, execute=partial(identify_intent_step, catalogue_names=()))
    with sessions() as db:
        state = load_checkpoint(db, **context).state
    assert state.intent == "explain_notice"
    assert state.procedure_candidates == []
    paused = run_worker_step(sessions, **context, execute=choose_candidate)
    assert paused.status == "waiting_for_information"

    client.app.include_router(build_reconnect_router(key=KEY))
    url = run_url(context)
    snapshot = client.get(url, headers=headers)
    assert snapshot.status_code == 200
    assert snapshot.json()["status"] == "waiting_for_information"
    replay = client.get(url + "/events", headers=headers)
    assert replay.status_code == 200
    assert replay.headers["Cache-Control"] == "private, no-store"
    question = replay.json()["events"][-1]["question"]
    assert question["missing_fields"] == [field]
    assert question["answer_shape"] == "free_text"
    assert question["answer_format"] == "redacted_excerpt"
    assert prompt in question["text"]
    assert hint in question["reply_hint"]
    assert ("issuing office" if language == "en" else "ufficio che ha emesso l’avviso") in question["reply_hint"]

    saved = client.post(f"{url}/questions/{question['question_id']}/reply", headers=headers, json={
        "client_reply_id": str(uuid4()), "expected_run_revision": snapshot.json()["run_revision"], **reply,
    })
    assert saved.status_code == 200
    assert saved.json()["type"] == "question.answered"
    restarted = sessionmaker(bind=sessions.kw["bind"])
    assert run_worker_step(restarted, **context, execute=choose_candidate).status == "completed"

    completed = client.get(url, headers=headers)
    assert completed.status_code == 200
    result = completed.json()["result"]
    assert result["verification_status"] == "insufficient_evidence"
    assert result["missing_information"] == [field]
    assert result["citations"] == []
    assert result["official_channel"] is None
    assert result["next_action"]["operation"] == "provide_information"
    assert ("issuing office" if language == "en" else "ufficio che ha emesso l’avviso") in result["explanation"]
    assert "16/12/2026" not in completed.text
    assert "documento sintetico" not in completed.text


@pytest.mark.parametrize("opening", [
    "The appointment date on the summons is not smudged. Can I submit by post?",
    "La data del modulo è illeggibile. Dove la scrivo?",
    "The notice requests a named attachment. Where do I send it?",
    "The letter gives my appointment date. The screenshot footer is unreadable.",
    "The appointment notice is clear. The date on the attachment is smudged.",
    "The notice names the requested attachment. The completed attachment itself is unreadable.",
])
def test_unreadable_notice_detection_preserves_unrelated_requests(opening):
    assert unreadable_notice_field(opening) is None


def test_explicit_case_selection_takes_precedence_over_a_notice_mention():
    message = StoredMessage("Open my other case. The date on the appointment notice is smudged.", "en", None)
    assert extract_intent(message, catalogue_names=()).intent == "resume_case"
