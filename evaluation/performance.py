"""One walk over the local workflows. No database and no priced call."""
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "backend"))
sys.path.insert(0, str(HERE))

from app import health, http_error
from extract import read
from knowledge import summarize
from model import complete
from retrieval import search
from starlette.exceptions import HTTPException
from tools import invoke

BUDGET = "budget: none approved"
COST = "cost: not priced"
USAGE = "usage: 0"
OPTIMIZATION = "optimization: none"
DB_LIMIT = "limit: the database is not opened"
PDF = b"%PDF-1.4\n(Name: Ada Lovelace) Tj\n(Via Torino 20, Milano) Tj\n%%EOF"
LOCAL = {"reply": "The model is not configured."}
NONE = {"outcome": "no evidence", "passages": []}


class _Url:
    path = "/v1/missing"


class _Request:
    url = _Url()


def _restore(previous):
    if previous is None:
        os.environ.pop("PAPERPILOT_MODEL", None)
    else:
        os.environ["PAPERPILOT_MODEL"] = previous


def _api():
    denied = http_error(_Request(), HTTPException(status_code=404))
    unknown = http_error(_Request(), HTTPException(status_code=418))
    return health() == {"status": "ok"} and denied.status_code == 404 and unknown.status_code == 418


def _model():
    previous = os.environ.get("PAPERPILOT_MODEL")
    calls = []
    os.environ["PAPERPILOT_MODEL"] = "local"
    try:
        got = complete("hello", lambda prompt: calls.append(prompt))
        os.environ["PAPERPILOT_MODEL"] = "configured"
        try:
            complete("hello")
            failed = False
        except RuntimeError:
            failed = True
        return calls == [] and got == LOCAL and failed
    finally:
        _restore(previous)


def _tool():
    found = invoke(
        "generate_checklist",
        {"case_id": "c1"},
        caller="ada",
        cases={"c1": {"person_id": "ada", "facts": {"language": "English"}}},
    )
    try:
        invoke("missing", {})
        rejected = False
    except ValueError:
        rejected = True
    return found.get("tool") == "generate_checklist" and "items" in found and rejected


def _document():
    good = read(PDF)
    bad = read(b"not a pdf")
    return good["status"] == "read" and good["name"] == "Ada Lovelace" and bad["status"] == "unreadable"


def _database():
    empty = search("", "address change", "Milano", "English")
    other = search("address", "other", "Milano", "English")
    return empty == NONE and other == NONE


def _one(_index):
    reply = complete("hello")
    bad = read(b"not a pdf")
    return reply["reply"], bad["status"]


def _load():
    previous = os.environ.get("PAPERPILOT_MODEL")
    os.environ["PAPERPILOT_MODEL"] = "local"
    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            rows = list(pool.map(_one, range(4)))
        return rows == [(LOCAL["reply"], "unreadable")] * 4
    finally:
        _restore(previous)


CHECKS = (
    ("api", _api),
    ("model", _model),
    ("tool", _tool),
    ("document", _document),
    ("database", _database),
    ("load", _load),
)


def walk():
    rows = []
    for name, probe in CHECKS:
        started = time.perf_counter()
        rows.append((name, bool(probe()), time.perf_counter() - started))
    return rows


def report(rows):
    lines = summarize(rows)
    if rows and all(ok for _name, ok, _seconds in rows):
        for name, _ok, _seconds in rows:
            lines.append(name + " held")
        lines.append(BUDGET)
        lines.append(COST)
        lines.append(USAGE)
        lines.append(OPTIMIZATION)
        lines.append(DB_LIMIT)
        lines.append("research: unreviewed")
        lines.append("performance ok")
    return lines
