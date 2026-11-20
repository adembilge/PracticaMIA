"""Measure synthetic conversation latency, tool checks and paid model spend."""

import argparse
from collections import Counter
import json
from math import ceil
from time import perf_counter_ns
from unittest.mock import patch

from app.agent import catalogue_evidence, worker
from app.agent.tool_execution import check_tool_execution

from score_phase04_next_action import ScenarioReplay, run as replay_development_set


VISIBLE_STATUSES = {"waiting_for_information", "waiting_for_approval", "completed", "failed", "stopped"}


class TimedReplay(ScenarioReplay):
    def __init__(self, sessions, data, case, language, catalog):
        super().__init__(sessions, data, case, language, catalog)
        self.worker_steps = 0
        self.tool_checks = Counter()
        self.requests = []

    def worker_step(self):
        self.worker_steps += 1
        return super().worker_step()

    def count_tool_check(self, db, *, call, **context):
        self.tool_checks[call.tool] += 1
        return check_tool_execution(db, call=call, **context)

    def step(self, step, *, question_was_aligned):
        if step["event"] not in {"message", "reply"}:
            return super().step(step, question_was_aligned=question_was_aligned)

        prior_steps = self.worker_steps
        with (
            patch.object(worker, "check_tool_execution", self.count_tool_check),
            patch.object(catalogue_evidence, "check_tool_execution", self.count_tool_check),
        ):
            started = perf_counter_ns()
            observed = super().step(step, question_was_aligned=question_was_aligned)
            elapsed_ms = (perf_counter_ns() - started) / 1_000_000
        dispatched = self.worker_steps > prior_steps
        visible = (
            dispatched and observed.blocked is None and self.snapshot is not None
            and self.snapshot.status in VISIBLE_STATUSES
        )
        self.requests.append({
            "id": step["id"],
            "event": step["event"],
            "dispatched": dispatched,
            "first_visible_state_ms": elapsed_ms if visible else None,
            "first_visible_state": self.snapshot.status if visible else None,
            "verified_response_ms": elapsed_ms if visible and observed.verified else None,
        })
        return observed

    def report(self, outcome, repetition):
        return {
            "id": outcome["id"],
            "repetition": repetition,
            "next_action_passed": outcome["passed"],
            "worker_steps": self.worker_steps,
            "server_tool_checks": dict(sorted(self.tool_checks.items())),
            # This adapter performs deterministic local computation and makes no paid calls.
            "model_calls": 0,
            "paid_model_cost_usd": 0,
            "requests": self.requests,
        }


def latency_summary(requests, key):
    samples = sorted(row[key] for row in requests if row[key] is not None)
    summary = {"samples": len(samples), "p50": None, "p95": None}
    if samples:
        summary["p50"] = round(samples[ceil(len(samples) * 0.50) - 1], 3)
        summary["p95"] = round(samples[ceil(len(samples) * 0.95) - 1], 3)
    return summary


def run(repetitions):
    if repetitions < 1:
        raise ValueError("The replay requires at least one repetition")

    cases = []
    for repetition in range(1, repetitions + 1):
        replays = []

        def build_replay(*args):
            replay = TimedReplay(*args)
            replays.append(replay)
            return replay

        result = replay_development_set(replay_factory=build_replay)
        cases.extend(
            replay.report(case, repetition) for replay, case in zip(replays, result["cases"], strict=True)
        )

    requests = [request for case in cases for request in case["requests"]]
    tool_checks = Counter()
    for case in cases:
        tool_checks.update(case["server_tool_checks"])
    case_count = len(cases)
    model_calls = sum(case["model_calls"] for case in cases)
    paid_cost = sum(case["paid_model_cost_usd"] for case in cases)
    return {
        "mode": "offline_synthetic_conversation_performance",
        "dataset_id": result["dataset_id"],
        "dataset_sha256": result["dataset_sha256"],
        "repetitions": repetitions,
        "case_runs": case_count,
        "scripted_requests": len(requests),
        "dispatched_requests": sum(row["dispatched"] for row in requests),
        "first_visible_state_ms": latency_summary(requests, "first_visible_state_ms"),
        "verified_response_ms": latency_summary(requests, "verified_response_ms"),
        "case_next_action_passes": sum(case["next_action_passed"] for case in cases),
        "worker_steps": sum(case["worker_steps"] for case in cases),
        "server_tool_checks": dict(sorted(tool_checks.items())),
        "model_calls": model_calls,
        "paid_model_cost_usd_per_case": paid_cost / case_count,
        "pilot_targets": None,
        "cases": cases,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeat", type=int, default=1, help="number of complete development-set runs")
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be at least 1")
    print(json.dumps(run(args.repeat), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
