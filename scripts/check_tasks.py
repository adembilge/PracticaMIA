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


def main():
    records = []
    for item in parse(PATH.read_text(encoding="utf-8")):
        missing = [field for field in FIELDS if field not in item]
        if missing:
            sys.exit("missing fields: " + ", ".join(missing))
        records.append({key: decode(key, item[key]) for key in FIELDS})
    ids = [record["id"] for record in records]
    if ids != list(range(1, 95)):
        sys.exit("ids are not 1 through 94 once")
    by_id = {record["id"]: record for record in records}
    decisions = (ROOT / "docs" / "DECISIONS.md").read_text(encoding="utf-8")
    for record in records:
        if record["status"] not in ("done", "not_started"):
            sys.exit("bad status on %s" % record["id"])
        if record["approval"] not in ("user", "none"):
            sys.exit("bad approval on %s" % record["id"])
        if record["status"] == "done" and record["verification"] != "artifact on main":
            sys.exit("silent done on %s" % record["id"])
        # shortcut: tasks 1-29 are already committed; the label is not a git lookup
        if (
            record["status"] == "done"
            and record["approval"] == "user"
            and record["id"] > 29
            and ("accepted: %s" % record["id"]) not in decisions
        ):
            sys.exit("missing acceptance for %s" % record["id"])
        for dep in record["depends"]:
            if dep >= record["id"] or dep not in by_id:
                sys.exit("bad dependency on %s" % record["id"])
    ready = [
        record["id"]
        for record in records
        if record["status"] == "not_started"
        and all(by_id[dep]["status"] == "done" for dep in record["depends"])
    ]
    if not ready:
        sys.exit("no next task")
    print("next: %s" % min(ready))


if __name__ == "__main__":
    main()
