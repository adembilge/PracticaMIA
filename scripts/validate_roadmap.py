"""Validate source-derived 12-stage/94-parent PracticaMIA task governance.

Run: python scripts/validate_roadmap.py
Requires PyYAML >=6 (CI installs a pinned version).
"""
from __future__ import annotations

from pathlib import Path
import re
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "PracticaMIA_Complete_Project_Specification.md"
TRACKER = ROOT / "docs" / "TASKS.yaml"
STAGE_PATTERN = re.compile(
    r"^## Stage (\d+) — ([^\n]+?) \(Tasks (\d+)–(\d+)\)", re.MULTILINE
)
TASK_PATTERN = re.compile(
    r"^\|\s*\*\*(\d+)\.\s+([^*]+)\*\*\s*\|\s*([^|]+)\|\s*([^|\n]+)\|",
    re.MULTILINE,
)
ALLOWED_STATES = {
    "pending", "eligible", "in_progress", "verification",
    "ready_for_review", "completed", "blocked", "failed",
}
SUBTASKS = {45, 50}


def expected_rows(spec_text: str):
    stages = [
        (int(m[1]), m[2], int(m[3]), int(m[4]))
        for m in STAGE_PATTERN.finditer(spec_text)
    ]
    tasks = [
        (int(m[1]), m[2].strip(), m[3].strip(), m[4].strip())
        for m in TASK_PATTERN.finditer(spec_text)
    ]
    return stages, tasks


def validate(data: dict, spec_text: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["Tracker must contain a YAML mapping"]
    stages, tasks = expected_rows(spec_text)
    if len(stages) != 12 or len(tasks) != 94:
        return ["Source specification no longer has 12 stages and exactly 94 tasks"]
    if [task[0] for task in tasks] != list(range(1, 95)):
        errors.append("Source task IDs must be 1 through 94 in order")
    if data.get("schema_version") != 1:
        errors.append("Unknown schema_version")
    if data.get("source_specification") != "PracticaMIA_Complete_Project_Specification.md":
        errors.append("Tracker does not cite the canonical specification")
    if not isinstance(data.get("reconciliation_required"), bool):
        errors.append("reconciliation_required must be boolean")
    if not isinstance(data.get("execution_blocked_until_reconciled"), bool):
        errors.append("execution_blocked_until_reconciled must be boolean")

    recorded_stages = data.get("stages")
    if not isinstance(recorded_stages, list) or len(recorded_stages) != 12:
        errors.append("Exactly 12 stages are required")
    else:
        for expected, found in zip(stages, recorded_stages):
            sid, name, start, end = expected
            if not isinstance(found, dict) or (
                found.get("id"), found.get("name"), found.get("task_range")
            ) != (sid, name, [start, end]):
                errors.append(f"Stage {sid} does not match canonical source")

    rows = data.get("tasks")
    if not isinstance(rows, list) or len(rows) != 94:
        return errors + ["Exactly 94 parent task records are required"]
    ids = [row.get("id") if isinstance(row, dict) else None for row in rows]
    if ids != list(range(1, 95)):
        errors.append("Parent task IDs must be unique, ordered, and 1 through 94")

    for i, item in enumerate(rows):
        if not isinstance(item, dict):
            errors.append(f"Task at index {i} is not a mapping")
            continue
        tid, title, objective, evidence = tasks[i]
        if item.get("id") != tid:
            errors.append(f"Incorrect ID at task position {i + 1}")
        stage = next((s[0] for s in stages if s[2] <= tid <= s[3]), None)
        if item.get("stage") != stage:
            errors.append(f"Task {tid} stage does not match source")
        for k, value in (
            ("title", title),
            ("objective", objective),
            ("completion_evidence", evidence),
        ):
            if item.get(k) != value:
                errors.append(f"Task {tid} {k} was changed from canonical source")
        dependencies = item.get("dependencies")
        if (not isinstance(dependencies, list)
                or any(type(x) is not int or not 1 <= x < tid for x in dependencies)
                or len(dependencies) != len(set(dependencies))):
            errors.append(f"Task {tid} dependencies must be unique earlier parent IDs")
        if tid == 55 and not {47, 53, 54}.issubset(set(dependencies or [])):
            errors.append("Task 55 is missing canonical explicit dependencies [47,53,54]")
        if item.get("status") not in ALLOWED_STATES:
            errors.append(f"Task {tid} has invalid status")
        if item.get("evidence_review") not in {
            "unreconciled", "verified", "partial", "blocked"
        }:
            errors.append(f"Task {tid} has invalid evidence_review")
        if not isinstance(item.get("requires_human_approval"), bool):
            errors.append(f"Task {tid} requires_human_approval must be boolean")
        if item.get("status") == "completed":
            if item.get("evidence_review") != "verified":
                errors.append(f"Task {tid} completed without verified evidence")
            links = item.get("evidence_links")
            if not isinstance(links, list) or not links or not all(
                isinstance(x, str) and x.strip() for x in links
            ):
                errors.append(f"Task {tid} completed without evidence_links")
            if item.get("requires_human_approval") and not item.get("approved_by"):
                errors.append(f"Task {tid} completed without human approval record")

        subtask_rows = item.get("subtasks")
        if tid not in SUBTASKS and subtask_rows is not None:
            errors.append(f"Task {tid} has unexpected subtasks")
        if tid in SUBTASKS:
            if not isinstance(subtask_rows, list) or len(subtask_rows) != 6:
                errors.append(f"Task {tid} must contain exactly six subtasks")
            else:
                expected_ids = [f"{tid}.{n}" for n in range(1, 7)]
                got = [
                    item.get("id") if isinstance(item, dict) else None
                    for item in subtask_rows
                ]
                if got != expected_ids:
                    errors.append(f"Task {tid} subtask IDs do not match source")
                for subtask in subtask_rows:
                    if not isinstance(subtask, dict) or not subtask.get("title"):
                        errors.append(f"Task {tid} has an invalid subtask")
                    elif subtask.get("status") not in ALLOWED_STATES:
                        errors.append(f"Task {tid} subtask has invalid status")

    if any(item.get("evidence_review") == "unreconciled" for item in rows if isinstance(item, dict)):
        if not data.get("reconciliation_required"):
            errors.append("Reconciliation cannot be cleared with unreconciled tasks")
        if not data.get("execution_blocked_until_reconciled"):
            errors.append("Execution cannot resume with unreconciled tasks")
    return errors


def main() -> int:
    try:
        source = SPEC.read_text(encoding="utf-8")
        data = yaml.safe_load(TRACKER.read_text(encoding="utf-8"))
        errors = validate(data, source)
    except (OSError, yaml.YAMLError) as exc:
        print(f"Roadmap validation error: {type(exc).__name__}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("PASS: 12 stages, 94 source-matched tasks, 12 RAG subtasks and evidence gates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
