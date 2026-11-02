"""Name and address, each with its line or marked unavailable."""
from classify import classify
from extract import _label, read

SCHEMA = ("name", "address")
SUPPORTED = ("lease", "ownership", "identity", "permit")
EMPTY = {"value": None, "page": None, "raw": None}


def _hit(pages, take):
    for page in pages:
        for line in page["text"].split("\n"):
            value = take(line)
            if value:
                return {"value": value, "page": page["page"], "raw": line}
    return None


def _address(line):
    return line if "Milano" in line else None


def fields(payload):
    kind = classify(payload)["type"]
    pages = read(payload)["pages"] if kind in SUPPORTED else []
    name = _hit(pages, _label)
    address = _hit(pages, _address)
    return {
        "type": kind,
        "name": name or EMPTY,
        "address": address or EMPTY,
    }
