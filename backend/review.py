"""The person confirms a value. A line is not proof."""
from fields import SCHEMA


def _state(field, slot):
    if slot["value"] is None:
        return "unavailable"
    raw = slot["raw"] or ""
    if field == "name" and (raw.startswith("Name:") or raw.startswith("Nome:")):
        return "unverified"
    return "flagged"


def review(found):
    out = {"type": found["type"]}
    for field in SCHEMA:
        slot = dict(found[field])
        if slot.get("review") != "verified":
            slot["review"] = _state(field, slot)
        out[field] = slot
    return out


def confirm(found, field, value):
    if field not in SCHEMA or not isinstance(value, str) or not value.strip():
        return None
    checked = review(found)
    slot = dict(checked[field])
    slot["value"] = value.strip()
    slot["review"] = "verified"
    checked[field] = slot
    return checked


def agreed(found):
    checked = found if "review" in found["name"] else review(found)
    return {
        field: checked[field]["value"] if checked[field]["review"] == "verified" else None
        for field in SCHEMA
    }
