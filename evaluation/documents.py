"""One walk over the synthetic papers. No threshold is approved."""
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "backend"))
sys.path.insert(0, str(HERE))

from classify import classify
from compare import compare
from fields import fields
from knowledge import summarize
from prepare import LINK, prepare
from review import agreed, confirm, review

LIMITS = (
    "limit: an image has no text layer",
    "limit: a date is not a field",
    "limit: an address is the first Milano line",
    "limit: case and commas are not a conflict",
    "limit: agreed trusts a review already on the dict",
    "limit: a missing name and address share one dict",
)


def _pdf(*lines):
    body = b"%PDF-1.4\n"
    for line in lines:
        body += b"(" + line.encode("latin-1") + b") Tj\n"
    return body + b"%%EOF"


def _png():
    data = (1).to_bytes(4, "big") + (1).to_bytes(4, "big") + b"\x08\x02\x00\x00\x00"
    return b"\x89PNG\r\n\x1a\n" + len(data).to_bytes(4, "big") + b"IHDR" + data + b"\x00\x00\x00\x00"


LEASE = _pdf(
    "Lease agreement",
    "Name: Ada Lovelace",
    "Via Torino 20, Milano",
    "Date: 01/11/2026",
)
OWNERSHIP = _pdf("Atto di proprieta", "Nome: Ada Lovelace")
PASSPORT = _pdf("Passport", "Via Torino 20, Milano")
MATCH = (
    {"type": "lease", "name": "Ada Lovelace", "address": "Via Torino 20, Milano"},
    {"type": "identity", "name": "ada  lovelace", "address": None},
    {"type": "permit", "name": "Ada Lovelace", "address": "via torino 20 milano"},
)
CONFLICT = (
    {"type": "lease", "name": "Ada Lovlace", "address": "Via Torino 20"},
    {"type": "identity", "name": "Ada Lovelace", "address": None},
    {"type": "permit", "name": "Ada Lovlace", "address": "Via Padova 10"},
)
S01 = {
    "language": "English",
    "f02": "Yes",
    "f04": "Via Torino 20, Milano",
    "f05": "named tenant",
    "non_eu": True,
    "f06": "Yes",
    "f07": "read",
    "f08": "read",
}
STATED = "Via Torino 20, Milano"


def _lease_address():
    found = fields(LEASE)
    values = (found["name"]["value"], found["address"]["value"])
    return found["address"]["value"] == "Via Torino 20, Milano" and "01/11/2026" not in values


def _chained():
    once = confirm(fields(LEASE), "name", "Ada Lovelace")
    twice = confirm(once, "address", "Via Dante 1, Milano")
    return (
        twice["name"]["review"] == "verified"
        and twice["address"]["review"] == "verified"
        and agreed(twice) == {"name": "Ada Lovelace", "address": "Via Dante 1, Milano"}
    )


def _compare_match():
    found = compare(MATCH, STATED)
    return found["name"]["status"] == "match" and found["address"]["status"] == "match"


def _compare_conflict():
    found = compare(CONFLICT)
    return (
        found["name"]["status"] == "conflict"
        and found["address"]["status"] == "conflict"
        and "chosen" not in found
    )


def _prepare_ready():
    found = prepare(S01, MATCH)
    return found["ready"] is True and found["link"] == LINK


def _prepare_blocked():
    found = prepare(S01, CONFLICT)
    return found["ready"] is False and found["link"] is None


CHECKS = (
    ("lease classify", lambda: classify(_pdf("Lease agreement", "Name: Ada Lovelace"))["type"] == "lease"),
    ("ownership classify", lambda: classify(_pdf("Atto di proprieta"))["type"] == "ownership"),
    ("identity classify", lambda: classify(_pdf("Passport"))["type"] == "identity"),
    ("permit classify", lambda: classify(_pdf("Permesso di soggiorno"))["type"] == "permit"),
    (
        "unknown classify",
        lambda: classify(_pdf("Dichiarazione di residenza"))["type"] == "unknown"
        and classify(_pdf("Please send the file"))["type"] == "unknown",
    ),
    ("ambiguous classify", lambda: classify(_pdf("Lease agreement", "Passport"))["type"] == "ambiguous"),
    ("image classify", lambda: classify(_png())["type"] == "unknown"),
    ("lease name", lambda: fields(LEASE)["name"]["value"] == "Ada Lovelace"),
    ("lease address", _lease_address),
    ("ownership name", lambda: fields(OWNERSHIP)["name"]["value"] == "Ada Lovelace"),
    ("ownership address", lambda: fields(OWNERSHIP)["address"]["value"] is None),
    ("identity name", lambda: fields(PASSPORT)["name"]["value"] is None),
    ("identity address", lambda: fields(PASSPORT)["address"]["value"] == "Via Torino 20, Milano"),
    (
        "review name",
        lambda: review(fields(LEASE))["name"]["review"] == "unverified"
        and agreed(review(fields(LEASE)))["name"] is None,
    ),
    (
        "review address",
        lambda: review(fields(LEASE))["address"]["review"] == "flagged"
        and agreed(review(fields(LEASE)))["address"] is None,
    ),
    ("review confirm", _chained),
    ("compare match", _compare_match),
    (
        "compare missing",
        lambda: compare(({"type": "ownership", "name": "Ada Lovelace", "address": None},))["address"]["status"]
        == "missing",
    ),
    ("compare conflict", _compare_conflict),
    ("prepare ready", _prepare_ready),
    ("prepare blocked", _prepare_blocked),
)


def walk():
    rows = []
    for name, check in CHECKS:
        started = time.perf_counter()
        rows.append((name, bool(check()), time.perf_counter() - started))
    return rows


def report(rows):
    lines = summarize(rows)
    lines.extend(LIMITS)
    if rows and all(ok for _name, ok, _seconds in rows):
        lines.append("documents ok")
    return lines
