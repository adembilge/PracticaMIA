"""Actions from the rules. A passage does not add a step."""

from checklist import checklist
from rules import evaluate

_PAPERS = ("open", "not ready", "ready")
_GAPS = ("missing", "blocked")


def _trace(evidence):
    if not isinstance(evidence, dict) or evidence.get("outcome") == "no evidence":
        return []
    rows = []
    for row in evidence.get("passages") or []:
        if (
            isinstance(row, dict)
            and row.get("review_status") == "trusted"
            and row.get("id")
            and row.get("source_id")
        ):
            rows.append(
                {
                    "id": row["id"],
                    "source_id": row["source_id"],
                    "review_status": "trusted",
                }
            )
    return rows


def _actions(facts, result):
    decision = result["decision"]
    rule = result["id"]
    if decision == "ask once":
        field = result.get("missing")
        if not field:
            return []
        return [{"id": field, "rule": rule, "mandatory": True}]
    if decision not in _PAPERS:
        return []
    return [
        {
            "id": item["id"],
            "rule": rule,
            "mandatory": decision != "ready" and item["state"] in _GAPS,
        }
        for item in checklist(facts)["items"]
    ]


def build(facts, evidence):
    result = evaluate(facts)
    return {
        "rule": result["id"],
        "decision": result["decision"],
        "evidence": _trace(evidence),
        "actions": _actions(facts, result),
    }
