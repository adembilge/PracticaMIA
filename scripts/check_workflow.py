"""Prove selection, the failure stops, and a fresh worktree."""
import copy
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_tasks

COPIES = ("docs/TASKS.yaml", "docs/DECISIONS.md", "scripts/check_tasks.py")


def expect(got, wanted):
    if got != wanted:
        sys.exit(got)


def row(records, task_id):
    return next(record for record in records if record["id"] == task_id)


def fresh():
    path = tempfile.mkdtemp(prefix="practicamia-workflow-")
    try:
        added = subprocess.run(
            ["git", "worktree", "add", "--detach", path],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if added.returncode != 0:
            sys.exit(added.stderr.strip() or "worktree add failed")
        # shortcut: detached HEAD misses an uncommitted edit, so copy the current backlog in
        for rel in COPIES:
            shutil.copyfile(ROOT / rel, Path(path) / rel)
        checked = subprocess.run(
            ["py", "-3", "scripts/check_tasks.py"],
            cwd=path,
            capture_output=True,
            text=True,
        )
        if checked.returncode != 0:
            sys.exit(checked.stderr.strip() or checked.stdout.strip() or "worktree check failed")
        return checked.stdout.strip()
    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", path],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        shutil.rmtree(path, ignore_errors=True)


def main():
    text = check_tasks.PATH.read_text(encoding="utf-8")
    decisions = (ROOT / "docs" / "DECISIONS.md").read_text(encoding="utf-8")
    records = check_tasks.load(text)
    live = check_tasks.report(records, decisions)
    if not live.startswith("next: "):
        sys.exit(live)

    silent = copy.deepcopy(records)
    task = row(silent, 35)
    task["status"] = "done"
    task["verification"] = "completion sentence"
    expect(check_tasks.report(silent, decisions), "silent done on 35")

    held = copy.deepcopy(records)
    task = row(held, 35)
    task["status"] = "done"
    task["approval"] = "user"
    task["verification"] = "artifact on main"
    expect(check_tasks.report(held, decisions), "missing acceptance for 35")

    blocked = copy.deepcopy(records)
    row(blocked, 35)["status"] = "ready"
    expect(check_tasks.report(blocked, decisions), "bad status on 35")

    expect(fresh(), live)
    print("workflow ok")


if __name__ == "__main__":
    main()
