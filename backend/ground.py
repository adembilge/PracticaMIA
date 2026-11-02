"""Claims from the rules. A passage body is not a claim."""

from plan import build
from procedure import select
from rules import evaluate

_OUTCOMES = ("no evidence", "insufficient evidence", "conflicting evidence")
_PAPERS = ("f07", "f08", "f09")


def _outcome(evidence):
    if isinstance(evidence, dict) and evidence.get("outcome") in _OUTCOMES:
        return evidence["outcome"]
    return "no evidence"


def _claims(facts, result, planned):
    claims = [
        {
            "kind": "decision",
            "rule": result["id"],
            "decision": result["decision"],
        }
    ]
    if result["decision"] in ("ask once", "unknown") and result.get("missing"):
        claims.append({"kind": "missing", "id": result["missing"]})
    door = select(facts).get("door")
    if door:
        claims.append({"kind": "door", "id": door})
    for action in planned["actions"]:
        if action.get("mandatory") and action.get("id") in _PAPERS:
            claims.append(
                {"kind": "document", "id": action["id"], "rule": result["id"]}
            )
    return claims


def check(facts, evidence):
    result = evaluate(facts)
    outcome = _outcome(evidence)
    return {
        "rule": result["id"],
        "decision": result["decision"],
        "outcome": outcome,
        "claims": _claims(facts, result, build(facts, evidence)),
        "escalate": outcome == "conflicting evidence",
    }
