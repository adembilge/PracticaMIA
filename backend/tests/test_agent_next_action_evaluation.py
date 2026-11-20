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

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agent.contract import AnswerResult
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
    }.issubset(passing)


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
