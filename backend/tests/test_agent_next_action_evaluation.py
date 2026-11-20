"""Exercise the offline next-action replay and its scoring boundary."""

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agent.contract import AnswerResult
from app.agent.reconnect_router import build_reconnect_router
from app.cases.intake_model import CaseIntake
from app.cases.model import CaseRecord


ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "evals/fixtures/phase04_agent_development.json"


def test_documented_next_action_command_reports_cases_and_turns():
    result = subprocess.run(
        [sys.executable, "evals/score_phase04_next_action.py"],
        env=os.environ | {"PYTHONPATH": str(ROOT / "backend")},
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    report = json.loads(result.stdout)
    dataset = DATASET.read_bytes()
    assert report["dataset_sha256"] == sha256(dataset).hexdigest()
    assert report["dataset_id"] == json.loads(dataset)["dataset_id"]

    cases = report["cases"]
    turns = [turn for case in cases for turn in case["turns"]]
    assert report["unassisted_next_action"]["total"] == len({case["id"] for case in cases}) == 26
    assert report["unassisted_next_action"]["passed"] == 24
    assert report["unassisted_next_action"]["passed"] == sum(
        all(turn["passed"] for turn in case["turns"]) for case in cases
    )
    diagnostics = report["diagnostics"]
    assert diagnostics["total_turns"] == len(turns) == 36
    assert diagnostics["correct_turns"] == sum(turn["passed"] for turn in turns)
    assert diagnostics["correct_authorities"] <= diagnostics["required_authorities"]
    assert diagnostics["supported_citations"] <= diagnostics["emitted_citations"]
    assert diagnostics["unnecessary_questions"] <= diagnostics["emitted_questions"]
    assert diagnostics["uncorrected_misrouting"] == sum(case["uncorrected_misrouting"] for case in cases)
    passing = {case["id"] for case in cases if case["passed"]}
    assert {
        "milan-confirmed-route:it", "milan-source-withdrawn:en", "milan-source-withdrawn:it",
        "current-attachment-limit:en", "current-attachment-limit:it",
        "destination-corrected:en", "destination-corrected:it",
        "torino-banns-and-delegation:en", "torino-banns-and-delegation:it",
        "permit-filing-route-missing:en", "permit-filing-route-missing:it",
        "permit-postal-intake:en", "permit-postal-intake:it",
        "two-goals-different-authorities:en", "two-goals-different-authorities:it",
    }.issubset(passing)


def test_confirmation_journey_scores_the_explicit_intake_action_and_keeps_exact_reviewed_handoff():
    result = subprocess.run(
        [sys.executable, "evals/score_phase04_next_action.py", "--confirmation-journey"],
        env=os.environ | {"PYTHONPATH": str(ROOT / "backend")},
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    report = json.loads(result.stdout)
    assert report["dataset_id"] == "phase04_agent_confirmation_journey_v2"
    assert report["dataset_sha256"] != sha256(DATASET.read_bytes()).hexdigest()
    assert report["unassisted_next_action"] == {"passed": 26, "total": 26, "pass_rate": 1.0}
    diagnostics = report["diagnostics"]
    assert diagnostics["correct_turns"] == diagnostics["total_turns"] == 40
    assert diagnostics["correct_authorities"] == diagnostics["required_authorities"] == 10
    assert diagnostics["supported_citations"] == diagnostics["required_citations"] == 30
    assert diagnostics["uncorrected_misrouting"] == 0
    baseline_data = json.loads(DATASET.read_bytes())
    baseline = next(case for case in baseline_data["cases"] if case["id"] == "resume-pending-destination")
    baseline_handoff = baseline["steps"][-1]["expect"]
    baseline_citations = sorted(
        passage for reference in baseline_handoff["citation_refs"]
        for passage in baseline_data["references"][reference]["signed_evidence"]["passage_ids"]
    )
    for case in report["cases"]:
        if case["id"].startswith("resume-pending-destination:"):
            _, _, pending, confirmed, final = case["turns"]
            assert pending["observed"]["fields"] == ["intake_confirmation"]
            assert not pending["observed"]["official_channel"]
            assert confirmed["observed"]["action"] == "saved_intake_confirmed"
            assert final["expected"]["action"] == baseline_handoff["next_action"]
            assert final["expected"]["authorities"] == baseline_handoff["authority_ids"]
            assert final["expected"]["citations"] == baseline_citations
            assert final["observed"]["official_channel"]


@pytest.mark.parametrize("language", ["en", "it"])
def test_reopened_case_confirms_through_owned_intake_before_fresh_verified_handoff(
    client, auth_headers, monkeypatch, language,
):
    monkeypatch.syspath_prepend(str(ROOT / "evals"))
    evaluator = importlib.import_module("score_phase04_next_action")
    data, _ = evaluator.load_development_set(confirmation_journey=True)
    case = next(case for case in data["cases"] if case["id"] == "resume-pending-destination")
    opening, _, reply, confirmation, followup = case["steps"]
    catalog = evaluator.load_catalog(evaluator.CATALOG.read_text(encoding="utf-8"))
    replay = evaluator.ScenarioReplay(client.app.state.session_factory, data, case, language, catalog)
    principal = replay.context["principal"]
    owner = auth_headers(principal.subject)
    outsider = auth_headers("bob")
    client.app.include_router(build_reconnect_router(
        key=replay.context["key"], read_evidence_scope=replay.read_scope,
    ))
    thread_url = f"/api/v1/agent/threads/{replay.context['thread_id']}"
    intake_url = f"/api/v1/cases/{replay.case_id}/intake"

    def send(step):
        response = client.post(thread_url + "/messages", headers=owner, json={
            "client_message_id": str(uuid4()), "language": language,
            "case_id": str(replay.case_id), "text": step["text"][language],
        })
        assert response.status_code == 202
        replay.context["run_id"] = UUID(response.json()["run_id"])
        replay.advance()
        return f"{thread_url}/runs/{response.json()['run_id']}"

    run_url = send(opening)
    reopened = client.get(run_url, headers=owner).json()
    assert reopened["status"] == "waiting_for_information"
    events = client.get(run_url + "/events", headers=owner).json()["events"]
    question = events[-1]["question"]
    assert question["missing_fields"] == ["destination"]
    saved = client.post(f"{run_url}/questions/{question['question_id']}/reply", headers=owner, json={
        "client_reply_id": str(uuid4()), "expected_run_revision": reopened["run_revision"],
        "text": reply["text"][language],
    })
    assert saved.status_code == 200
    replay.advance()
    waiting = client.get(run_url, headers=owner).json()
    assert waiting["selected_case"]["case_id"] == str(replay.case_id)
    assert waiting["result"]["next_action"]["operation"] == "confirm_saved_intake"
    assert waiting["result"]["citations"] == [] and waiting["handoff"] is None
    assert client.get(run_url, headers=outsider).status_code == 404

    draft = client.get(intake_url, headers=owner).json()
    assert not draft["confirmed"] and "destination_municipality" not in draft["facts"]
    draft_facts = draft["facts"] | confirmation["facts"]
    for facts in (draft["facts"], draft_facts):
        draft_response = client.put(intake_url, headers=owner, json={"facts": facts, "confirm": False})
        assert draft_response.status_code == 200 and not draft_response.json()["confirmed"]
        early_url = send(followup)
        early = client.get(early_url, headers=owner).json()
        assert early["selected_case"]["case_id"] == str(replay.case_id)
        assert early["result"]["next_action"]["operation"] == "confirm_saved_intake"
        assert early["result"]["missing_information"] == ["intake_confirmation"]
        assert early["handoff"] is None and early["result"]["citations"] == []
        assert client.get(early_url, headers=outsider).status_code == 404
        assert client.get(intake_url, headers=owner).json() == draft_response.json()

    payload = {"facts": draft_facts, "confirm": True}
    assert client.put(intake_url, headers=outsider, json=payload).status_code == 404
    response = client.put(intake_url, headers=owner, json=payload)
    assert response.status_code == 200 and response.json()["confirmed"]
    replay.facts.update(response.json()["facts"])

    verified = client.get(send(followup), headers=owner).json()
    assert verified["result"]["verification_status"] == "verified"
    assert verified["handoff"]["next_action"]["operation"] == "open_official_channel"
    assert set(verified["handoff"]["evidence_ids"]) == {item.citation.passage_id for item in replay.channel_passages}
    assert client.get(run_url, headers=owner).json()["handoff"] is None
    archived = client.patch(f"/api/v1/cases/{replay.case_id}/archive", headers=owner, json={"archived": True})
    assert archived.status_code == 200
    assert client.get(run_url, headers=owner).json()["selected_case"] is None


def _replay(monkeypatch, case_id, *, opening, invalidate_case=None):
    monkeypatch.syspath_prepend(str(ROOT / "evals"))
    evaluator = importlib.import_module("score_phase04_next_action")
    data = json.loads(DATASET.read_bytes())
    case = deepcopy(next(case for case in data["cases"] if case["id"] == case_id))
    case["steps"][0]["text"]["en"] = opening
    catalog = evaluator.load_catalog(evaluator.CATALOG.read_text(encoding="utf-8"))
    engine = create_engine("sqlite+pysqlite:///:memory:")
    try:
        evaluator.Base.metadata.create_all(engine)
        replay = evaluator.ScenarioReplay(sessionmaker(bind=engine), data, case, "en", catalog)
        if invalidate_case is not None:
            execute = replay.execute

            def invalidate_before_publication(message, state):
                result = execute(message, state)
                if state.uses_confirmed_case_scope and isinstance(result, AnswerResult):
                    assert result.verification_status == "verified"
                    with replay.sessions.begin() as db:
                        invalidate_case(db, str(replay.case_id))
                return result

            replay.execute = invalidate_before_publication
        scored = evaluator.score_case(replay, case, data["references"])
        return scored, replay.snapshot
    finally:
        engine.dispose()


def test_replay_withdraws_current_handoff_but_retains_the_historical_answer(monkeypatch):
    report, saved = _replay(
        monkeypatch, "milan-source-withdrawn", opening="How do I file my registered address change in Milan?",
    )
    before, after = report["turns"]
    assert before["passed"] and before["observed"]["official_channel"]
    assert after["passed"] and after["observed"]["action"] == "revalidate_sources"
    assert not after["observed"]["official_channel"] and after["observed"]["citations"] == ()
    assert saved.result.official_channel is not None and saved.result.citations


def test_replay_withholds_scripted_reply_after_a_different_question(monkeypatch):
    report, saved = _replay(monkeypatch, "resume-pending-destination", opening="Hello")
    opening, restore, reply = report["turns"]
    assert opening["observed"]["fields"] == ("intent",) and opening["unnecessary_question"]
    assert restore["observed"]["blocked"] == reply["observed"]["blocked"] == "required_question_mismatch"
    assert not report["passed"] and saved.status == "waiting_for_information"


@pytest.mark.parametrize("invalidate", ["archive", "unconfirm"])
def test_saved_filing_rechecks_the_case_before_publishing_a_reviewed_channel(monkeypatch, invalidate):
    def invalidate_case(db, case_id):
        if invalidate == "archive":
            db.get(CaseRecord, case_id).archived_at = datetime.now(timezone.utc)
        else:
            db.get(CaseIntake, case_id).confirmed_at = None

    report, saved = _replay(
        monkeypatch, "milan-source-withdrawn", opening="Show the filing step for my saved Milan case.",
        invalidate_case=invalidate_case,
    )
    assert not report["passed"]
    assert saved.result.verification_status == "insufficient_evidence"
    assert saved.result.official_channel is None and saved.result.citations == []
    assert saved.result.next_action.operation == "provide_information"


def test_outdated_upload_limit_gives_a_form_check_without_reusing_the_number(monkeypatch):
    report, saved = _replay(
        monkeypatch, "current-attachment-limit",
        opening="An older ANPR handbook says 7 MB. What maximum upload applies in the current ANPR form?",
    )
    assert report["passed"]
    assert saved.result.verification_status == "insufficient_evidence"
    assert saved.result.next_action.operation == "check_current_form"
    assert saved.result.official_channel is None and saved.result.citations == []
    assert "7 MB" not in saved.result.explanation
