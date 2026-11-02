"""The intake list for one open case. The case row stays the store."""

from prepare import _story
from procedure import select

IGNORED = ("research", "deadline", "paper", "sign_in")
BLOCKED = ("failed", "unreadable")
NONE = {"items": [], "missing": None}


def _present(facts, key):
    value = facts.get(key)
    return key in facts and value is not None and not (isinstance(value, str) and not value.strip())


def _paper(facts, key):
    if not _present(facts, key) or facts[key] == "missing":
        return "missing"
    if facts[key] in BLOCKED:
        return "blocked"
    if facts[key] == "read":
        return "done"
    return "missing"


def _gap(items):
    for item in items:
        if item["state"] in ("missing", "blocked"):
            return item["id"]
    return None


def checklist(facts):
    story = {key: value for key, value in facts.items() if key not in IGNORED}
    if select(story).get("procedure") != "address change":
        return dict(NONE)
    f07 = _paper(story, "f07")
    items = [{"id": "f07", "state": f07}]
    papers_done = f07 == "done"
    if story.get("non_eu"):
        if not _present(story, "f08") and not papers_done:
            f08 = "waiting"
        else:
            f08 = _paper(story, "f08")
        items.append({"id": "f08", "state": f08})
        papers_done = papers_done and f08 == "done"
    if not papers_done:
        f09 = "waiting"
    elif not _present(story, "f09"):
        f09 = "missing"
    elif story.get("f09") in ("disagree", "mismatch") and not story.get("named"):
        f09 = "blocked"
    elif story.get("f09") == "agree" or story.get("named"):
        f09 = "done"
    else:
        f09 = "missing"
    items.append({"id": "f09", "state": f09})
    return {"items": items, "missing": _gap(items)}


def _status(value):
    if value in ("read", "failed", "unreadable"):
        return value
    return "missing"


def stored(row, uploads):
    facts = {}
    for key in ("language", "f02", "f03", "f04", "f05", "f06"):
        value = row[key]
        if isinstance(value, str) and value:
            facts[key] = value
    if facts.get("f06") == "Yes":
        facts["non_eu"] = True
    papers = []
    for item in uploads:
        status = _status(item["status"])
        if item["role"] == "title":
            facts["f07"] = status
            kind = "ownership" if facts.get("f05") == "Owner" else "lease"
        elif item["role"] == "identity":
            facts["f08"] = status
            kind = "permit"
        else:
            continue
        if status == "read":
            papers.append(
                {
                    "type": kind,
                    "name": item.get("extracted_name"),
                    "address": item.get("extracted_address"),
                }
            )
    named = None
    if isinstance(row.get("named_name"), str) and isinstance(row.get("named_address"), str):
        named = {"name": row["named_name"], "address": row["named_address"]}
    return facts, papers, named


def from_stored(row, uploads):
    facts, papers, named = stored(row, uploads)
    story, _compared = _story(facts, papers, named)
    return checklist(story)
