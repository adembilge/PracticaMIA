"""The package is the agreed name and address. It does not file."""
from compare import TITLE, compare
from rules import evaluate

LINK = "https://www.anagrafenazionale.interno.it/servizi-al-cittadino/"
TEMPLATE = ("name", "address", "link")
GAPS = {"R-06": "f07", "R-07": "f09", "f08": "f08"}


def _named(named):
    if not isinstance(named, dict):
        return None
    name = named.get("name")
    address = named.get("address")
    if not isinstance(name, str) or not isinstance(address, str):
        return None
    name = name.strip()
    address = address.strip()
    if not name or not address:
        return None
    return {"name": name, "address": address}


def _title(column):
    for item in column["values"]:
        if item["type"] in TITLE:
            return item["value"]
    return None


def _story(facts, papers, chosen):
    story = dict(facts)
    stated = story.get("f04")
    compared = compare(papers, stated if isinstance(stated, str) else None)
    conflict = compared["name"]["status"] == "conflict" or compared["address"]["status"] == "conflict"
    match = compared["name"]["status"] == "match" and compared["address"]["status"] == "match"
    story.pop("named", None)
    if chosen and conflict:
        story["named"] = True
        story["f09"] = "disagree"
    elif match:
        story["f09"] = "agree"
    elif conflict:
        story["f09"] = "disagree"
    else:
        story.pop("f09", None)
    return story, compared


def _gaps(decision):
    if decision.get("missing"):
        return [decision["missing"]]
    return [GAPS.get(decision["id"], decision["id"])]


def prepare(facts, papers, named=None):
    chosen = _named(named)
    story, compared = _story(facts, papers, chosen)
    decision = evaluate(story)
    ready = decision["decision"] == "ready"
    values = {"name": None, "address": None, "link": None}
    if ready and chosen and story.get("named"):
        values = {"name": chosen["name"], "address": chosen["address"], "link": LINK}
    elif ready:
        stated = story.get("f04")
        address = stated.strip() if isinstance(stated, str) and stated.strip() else _title(compared["address"])
        name = _title(compared["name"])
        if name and address:
            values = {"name": name, "address": address, "link": LINK}
        else:
            ready = False
    return {
        "ready": ready,
        "missing": [] if ready else _gaps(decision),
        "warnings": compared,
        **{key: values[key] for key in TEMPLATE},
    }
