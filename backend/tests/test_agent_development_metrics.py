"""Exercise the offline evaluation through its documented command."""

from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "evals/fixtures/phase04_agent_development.json"


def test_component_evaluation_reports_independent_replayable_results():
    command = [sys.executable, "evals/score_phase04_agent.py"]
    environment = os.environ | {"PYTHONPATH": str(ROOT / "backend")}
    result = subprocess.run(command, env=environment, cwd=ROOT, capture_output=True, text=True, check=True)
    repeat = subprocess.run(command, env=environment, cwd=ROOT, capture_output=True, text=True, check=True)
    assert repeat.stdout == result.stdout

    report = json.loads(result.stdout)
    dataset = DATASET.read_bytes()
    assert report["dataset_id"] == json.loads(dataset)["dataset_id"]
    assert report["dataset_sha256"] == sha256(dataset).hexdigest()
    metrics = report["metrics"]
    assert {name: metric["total"] for name, metric in metrics.items()} == {
        "intent": 26,
        "procedure_retrieval": 26,
        "evidence": 20,
        "question_quality": 22,
        "tool_authorization": 9,
    }
    for metric in metrics.values():
        rows = metric["rows"]
        assert len({row["id"] for row in rows}) == len(rows) == metric["total"]
        assert all(row["passed"] == (row["expected"] == row["observed"]) for row in rows)
        assert sum(row["passed"] for row in rows) == metric["passed"]
        assert round(metric["passed"] / metric["total"], 4) == metric["pass_rate"]

    evidence = {
        row["id"]: row for row in metrics["evidence"]["rows"]
        if row["id"].startswith("milan-source-withdrawn:")
    }
    for language in ("en", "it"):
        rows = [row for key, row in evidence.items() if f":{language}:" in key]
        before, after = rows
        assert before["observed"] == before["expected"] != []
        assert after["observed"] == after["expected"] == []

    tool_results = {row["id"]: row["observed"] for row in metrics["tool_authorization"]["rows"]}
    assert tool_results["owned_running_read"] == "allowed"
    assert tool_results["foreign_principal_read"] == tool_results["paused_read"] == "denied"
    assert tool_results["write_without_approval"] == "denied"
