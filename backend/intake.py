"""One missing field. A known answer stays on the case."""

from intent import read
from rules import evaluate

_LISTS = {
    "f02": {"Yes", "never registered in Italy", "registered in another municipality"},
    "f03": {"Owner, alone", "named tenant, alone", "guest", "another adult"},
    "f05": {"Owner", "named tenant"},
    "f06": {"Yes", "No"},
    "f07": {"missing", "failed", "unreadable"},
    "f09": {"disagree", "mismatch"},
}
_RESEARCH = ("deadline", "paper", "sign_in")


def blank():
    return {"facts": {}, "asked": [], "asking": None}


def _copy(case):
    return {
        "facts": dict(case.get("facts") or {}),
        "asked": list(case.get("asked") or []),
        "asking": case.get("asking"),
    }


def _valid(key, value):
    if key == "f04":
        return isinstance(value, str) and "Milano" in value
    if key == "language":
        return isinstance(value, str) and bool(value.strip())
    return key in _LISTS and value in _LISTS[key]


def _merge(case, stated):
    for key, value in stated.items():
        if key in ("question",) or key in _RESEARCH:
            continue
        if not _valid(key, value):
            continue
        if key in case["facts"]:
            continue
        case["facts"][key] = value


def _probe(facts, stated, asked):
    probe = dict(facts)
    question = stated.get("question")
    if question in ("f02", "f03") and question not in facts:
        probe["question"] = question
        if question in asked:
            probe["asked"] = True
    return probe


def _next(result):
    decision = result["decision"]
    if decision == "ask once":
        return result.get("missing")
    if decision == "open":
        return "f07"
    if decision == "unknown":
        return result.get("missing")
    return None


def _ask(case, stated):
    result = evaluate(_probe(case["facts"], stated, case["asked"]))
    field = _next(result)
    if field and field not in case["asked"]:
        case["asked"].append(field)
        case["asking"] = field
    else:
        case["asking"] = None
    return case


def turn(case, message):
    current = _copy(case)
    if "password" in message.lower():
        current["asking"] = None
        return current
    found = read(message)
    if any(found["stated"].get(key) for key in _RESEARCH):
        current["asking"] = None
        return current
    if current["asking"]:
        field = current["asking"]
        answer = " ".join(message.split())
        current["asking"] = None
        if not _valid(field, answer):
            return current
        current["facts"][field] = answer
        return _ask(current, {})
    _merge(current, found["stated"])
    return _ask(current, found["stated"])
