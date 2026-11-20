"""Check performance samples against the replayed request and case boundaries."""

import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]


def test_performance_report_keeps_unverified_and_undispatched_requests_out_of_latency_samples():
    result = subprocess.run(
        [sys.executable, "evals/measure_phase04_agent.py"],
        env=os.environ | {"PYTHONPATH": str(ROOT / "backend")},
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    report = json.loads(result.stdout)
    cases = report["cases"]
    requests = [request for case in cases for request in case["requests"]]
    assert report["case_runs"] == len({case["id"] for case in cases}) == 26
    assert report["scripted_requests"] == len(requests)
    assert report["dispatched_requests"] == sum(request["dispatched"] for request in requests)
    assert {request["event"] for request in requests} == {"message", "reply"}
    for key in ("first_visible_state_ms", "verified_response_ms"):
        samples = [request[key] for request in requests if request[key] is not None]
        summary = report[key]
        assert summary["samples"] == len(samples) > 0
        assert 0 <= summary["p50"] <= summary["p95"]
    assert report["verified_response_ms"]["samples"] < report["first_visible_state_ms"]["samples"]
    for request in requests:
        if not request["dispatched"]:
            assert request["first_visible_state_ms"] is None and request["verified_response_ms"] is None
        if request["verified_response_ms"] is not None:
            assert request["first_visible_state"] == "completed"
            assert request["verified_response_ms"] == request["first_visible_state_ms"]

    assert report["worker_steps"] == sum(case["worker_steps"] for case in cases)
    assert report["server_tool_checks"]["read_case_context"] == sum(
        case["server_tool_checks"].get("read_case_context", 0) for case in cases
    ) > 0
    assert report["case_next_action_passes"] == sum(case["next_action_passed"] for case in cases)
    assert report["model_calls"] == report["paid_model_cost_usd_per_case"] == 0
    assert report["pilot_targets"] is None
