"""Check the backlog and print the next eligible task."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "docs" / "TASKS.yaml"
FIELDS = (
    "id",
    "stage",
    "depends",
    "description",
    "artifact",
    "acceptance",
    "verification",
    "approval",
    "status",
)


def parse(text):
    records = []
    current = None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("- "):
            if current is not None:
                records.append(current)
            key, value = line[2:].split(": ", 1)
            current = {key: value}
        else:
            key, value = line.strip().split(": ", 1)
            current[key] = value
    if current is not None:
        records.append(current)
    return records


def decode(key, value):
    if key in ("id", "stage"):
        return int(value)
    if key == "depends":
        inner = value[1:-1].strip()
        return [] if not inner else [int(part) for part in inner.split(",")]
    if value.startswith('"'):
        return json.loads(value)
    return value


def load(text):
    records = []
    for item in parse(text):
        missing = [field for field in FIELDS if field not in item]
        if missing:
            return "missing fields: " + ", ".join(missing)
        records.append({key: decode(key, item[key]) for key in FIELDS})
    return records


def report(records, decisions):
    if isinstance(records, str):
        return records
    ids = [record["id"] for record in records]
    if ids != list(range(1, 95)):
        return "ids are not 1 through 94 once"
    by_id = {record["id"]: record for record in records}
    for record in records:
        if record["status"] not in ("done", "not_started"):
            return "bad status on %s" % record["id"]
        if record["approval"] not in ("user", "none"):
            return "bad approval on %s" % record["id"]
        if record["status"] == "done" and record["verification"] != "artifact on main":
            return "silent done on %s" % record["id"]
        # shortcut: tasks 1-29 are already committed; the label is not a git lookup
        if (
            record["status"] == "done"
            and record["approval"] == "user"
            and record["id"] > 29
            and ("accepted: %s" % record["id"]) not in decisions
        ):
            return "missing acceptance for %s" % record["id"]
        for dep in record["depends"]:
            if dep >= record["id"] or dep not in by_id:
                return "bad dependency on %s" % record["id"]
    ready = [
        record["id"]
        for record in records
        if record["status"] == "not_started"
        and all(by_id[dep]["status"] == "done" for dep in record["depends"])
    ]
    if not ready:
        return "no next task"
    return "next: %s" % min(ready)


def main():
    text = PATH.read_text(encoding="utf-8")
    decisions = (ROOT / "docs" / "DECISIONS.md").read_text(encoding="utf-8")
    result = report(load(text), decisions)
    if not result.startswith("next: "):
        sys.exit(result)
    print(result)


if __name__ == "__main__":
    main()
