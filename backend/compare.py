"""Show both values. Do not pick one."""
SUPPORTED = ("lease", "ownership", "identity", "permit")
TITLE = ("lease", "ownership")


def _norm(value):
    if not isinstance(value, str):
        return None
    text = " ".join(value.casefold().replace(",", " ").split())
    return text or None


def _column(papers, field, stated):
    present = []
    absent = []
    for paper in papers:
        kind = paper.get("type")
        if kind not in SUPPORTED:
            continue
        value = paper.get(field)
        if field == "address" and kind not in TITLE and _norm(value) is None:
            continue
        if _norm(value) is None:
            absent.append(kind)
        else:
            present.append({"type": kind, "value": value.strip()})
    if field == "address" and _norm(stated):
        present.append({"type": "stated", "value": stated.strip()})
    keys = {_norm(item["value"]) for item in present}
    if len(keys) > 1:
        status = "conflict"
    elif absent or not keys:
        status = "missing"
    else:
        status = "match"
    return {"status": status, "values": present, "absent": absent}


def compare(papers, stated=None):
    return {
        "name": _column(papers, "name", None),
        "address": _column(papers, "address", stated),
    }
