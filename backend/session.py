"""One case checkpoint. A retry does not run the step again."""

import copy

import intake
from graph import build

# shortcut: the dict is the checkpoint, upgrade when a turn is allowed to write the case row.
LIMIT = 8


def _blank():
    return {
        "facts": {},
        "asked": [],
        "asking": None,
        "seen": [],
        "tools": {},
        "turn": None,
        "steps": 0,
    }


def _copy(state):
    return copy.deepcopy(state)


def _load(store, case_id):
    saved = store.get(case_id)
    if not isinstance(saved, dict):
        return _blank()
    return _copy(saved)


def _evidence(evidence):
    passages = []
    for row in (evidence or {}).get("passages") or []:
        if not isinstance(row, dict):
            continue
        passages.append(
            {
                "id": row.get("id"),
                "source_id": row.get("source_id"),
                "review_status": row.get("review_status"),
            }
        )
    return {"outcome": (evidence or {}).get("outcome"), "passages": passages}


def resume(store, case_id):
    return _load(store, case_id)


def turn(store, case_id, message, key):
    current = _load(store, case_id)
    if key in current["seen"]:
        return current
    if "password" in message.lower():
        return current
    if current["steps"] >= LIMIT:
        return current
    updated = intake.turn(current, message)
    updated["seen"] = current["seen"] + [key]
    updated["tools"] = current["tools"]
    updated["turn"] = current["turn"]
    updated["turn_key"] = current.get("turn_key")
    updated["steps"] = current["steps"] + 1
    store[case_id] = updated
    return _copy(updated)


def call(store, case_id, name, payload, key, invoke):
    current = _load(store, case_id)
    if key in current["tools"]:
        return _copy(current["tools"][key])
    if current["steps"] >= LIMIT:
        return None
    result = invoke(name, payload)
    current["tools"][key] = _copy(result)
    current["steps"] = current["steps"] + 1
    store[case_id] = current
    return _copy(current["tools"][key])


def run(store, case_id, state, key, search=None, evaluate=None):
    current = _load(store, case_id)
    if current.get("turn_key") == key and current["turn"] is not None:
        return _copy(current["turn"])
    if current["steps"] >= LIMIT:
        return None if current["turn"] is None else _copy(current["turn"])
    result = build(search, evaluate).invoke(state)
    current["turn"] = {
        "facts": dict(result.get("facts") or {}),
        "decision": result.get("decision"),
        "evidence": _evidence(result.get("evidence")),
    }
    current["turn_key"] = key
    current["steps"] = current["steps"] + 1
    store[case_id] = current
    return _copy(current["turn"])
