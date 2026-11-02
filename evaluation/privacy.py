"""One walk over the privacy boundaries. No database and no legal review."""
import logging
import os
import secrets
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "backend"))
sys.path.insert(0, str(HERE))

from app import http_error, log
from auth import _expired, database_url
from case import PUBLIC, _accepted
from knowledge import summarize
from model import complete
from models import AuditEvent, Case, Message, Passage, Person, Session, Upload
from starlette.exceptions import HTTPException
from tools import invoke
from upload import LIMIT, _fields, _safe, upload_dir

FORBIDDEN = {"password", "secret", "credential", "email"}
PRIVATE = (Person, Case, Message, Upload, Session, AuditEvent)
REMEDIATION = (
    "remediation: a person row has no credential, a log line is the status and the path, "
    "and deleting the person cascades the case"
)
LIMIT_LINE = "limit: the cascade is the model foreign key, not a live delete"
LEGAL = "legal: separate"


def _names(model):
    return set(model.__table__.columns.keys())


def _ondelete(column):
    return next(iter(column.foreign_keys)).ondelete


def _account():
    return _names(Person) == {"id"} and _names(Person).isdisjoint(FORBIDDEN)


def _authorization():
    other = invoke(
        "generate_checklist",
        {"case_id": "c1"},
        caller="bea",
        cases={"c1": {"person_id": "ada", "facts": {"language": "English"}}},
    )
    hidden = {"path", "password", "named_name", "named_address"}
    return other["items"] == [] and other["missing"] is None and hidden.isdisjoint(PUBLIC)


def _file():
    pdf = b"%PDF-1.4\n(Name: Ada) Tj\n%%EOF"
    directory = Path(upload_dir()).resolve()
    path = (directory / (secrets.token_urlsafe() + ".pdf")).resolve()
    outside = (directory / ".." / "secret.txt").resolve()
    return (
        _safe(pdf)
        and not _safe(b"%PDF-1.4\n/JavaScript\n%%EOF")
        and not _safe(b"password")
        and path.is_relative_to(directory)
        and path.parent == directory
        and not outside.is_relative_to(directory)
        and LIMIT == 10 * 1024 * 1024
    )


def _session():
    now = datetime.now(timezone.utc)
    return (
        _expired({"expires_at": now - timedelta(seconds=1)})
        and not _expired({"expires_at": now + timedelta(hours=1)})
        and not _expired({"expires_at": None})
        and _names(Session).isdisjoint(FORBIDDEN)
        and "body" not in _names(Session)
    )


def _multipart(parts):
    boundary = "bound"
    chunks = []
    for name, data in parts:
        chunks.append(
            (
                '--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n' % (boundary, name)
            ).encode()
            + data
            + b"\r\n"
        )
    chunks.append(("--%s--\r\n" % boundary).encode())
    return "multipart/form-data; boundary=%s" % boundary, b"".join(chunks)


def _input():
    ctype, raw = _multipart((("role", b"title"), ("file", b"%PDF")))
    extra, poisoned = _multipart((("role", b"title"), ("file", b"%PDF"), ("password", b"secret")))
    body = {
        "person_id": "ada",
        "language": "English",
        "f02": "Yes",
        "f04": "Via Torino 20, Milano",
        "f05": "named tenant",
        "password": "secret",
    }
    return _fields(ctype, raw) is not None and _fields(extra, poisoned) is None and not _accepted(body, True)


def _secret():
    url = database_url()
    return (
        "password" not in url
        and "secret" not in url
        and all(_names(model).isdisjoint(FORBIDDEN) for model in PRIVATE)
    )


def _log():
    records = []

    class Grab(logging.Handler):
        def emit(self, record):
            records.append(record.getMessage())

    handler = Grab()
    level = log.level
    log.setLevel(logging.INFO)
    log.addHandler(handler)
    try:
        http_error(type("Req", (), {"url": type("Url", (), {"path": "/v1/person"})()})(), HTTPException(400, "password secret"))
    finally:
        log.removeHandler(handler)
        log.setLevel(level)
    return records == ["400 /v1/person"] and _names(AuditEvent) == {"id", "case_id", "action"}


def _deletion():
    handle, name = tempfile.mkstemp()
    os.close(handle)
    missing = name + "-gone"
    try:
        removed = []
        for path in (name, missing, None):
            if path and os.path.isfile(path):
                os.remove(path)
                removed.append(path)
        return (
            removed == [name]
            and not os.path.isfile(name)
            and _ondelete(Case.__table__.c.person_id) == "CASCADE"
            and all(_ondelete(model.__table__.c.case_id) == "CASCADE" for model in (Message, Upload, Session, AuditEvent))
            and "person_id" not in _names(Passage)
        )
    finally:
        if os.path.isfile(name):
            os.remove(name)


def _model():
    previous = os.environ.get("PAPERPILOT_MODEL")
    os.environ["PAPERPILOT_MODEL"] = "local"
    calls = []
    try:
        got = complete("my password is secret", lambda prompt: calls.append(prompt))
        return calls == [] and got == {"reply": "The model is not configured."} and "password" not in got["reply"]
    finally:
        if previous is None:
            os.environ.pop("PAPERPILOT_MODEL", None)
        else:
            os.environ["PAPERPILOT_MODEL"] = previous


CHECKS = (
    ("account", _account),
    ("authorization", _authorization),
    ("file", _file),
    ("session", _session),
    ("input", _input),
    ("secret", _secret),
    ("log", _log),
    ("deletion", _deletion),
    ("model", _model),
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
        lines.append("blocking: none")
        lines.append(REMEDIATION)
        lines.append(LIMIT_LINE)
        lines.append(LEGAL)
        lines.append("research: unreviewed")
        lines.append("privacy ok")
    return lines
