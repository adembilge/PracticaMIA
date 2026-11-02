"""A value keeps its line, or it is unavailable."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fields import fields

EMPTY = {"value": None, "page": None, "raw": None}


def _pdf(*lines):
    body = b"%PDF-1.4\n"
    for line in lines:
        body += b"(" + line.encode("latin-1") + b") Tj\n"
    return body + b"%%EOF"


def _png():
    data = (1).to_bytes(4, "big") + (1).to_bytes(4, "big") + b"\x08\x02\x00\x00\x00"
    return b"\x89PNG\r\n\x1a\n" + len(data).to_bytes(4, "big") + b"IHDR" + data + b"\x00\x00\x00\x00"


def _linked(value, raw):
    return {"value": value, "page": 1, "raw": raw}


def _open(kind, name=EMPTY, address=EMPTY):
    return {"type": kind, "name": name, "address": address}


FIXTURES = (
    (
        _pdf(
            "Lease agreement",
            "Name: Ada Lovelace",
            "Via Torino 20, Milano",
            "Date: 01/11/2026",
        ),
        _open(
            "lease",
            _linked("Ada Lovelace", "Name: Ada Lovelace"),
            _linked("Via Torino 20, Milano", "Via Torino 20, Milano"),
        ),
    ),
    (
        _pdf("Atto di proprieta", "Nome: Ada Lovelace"),
        _open("ownership", _linked("Ada Lovelace", "Nome: Ada Lovelace")),
    ),
    (
        _pdf("Passport", "Via Torino 20, Milano"),
        _open("identity", address=_linked("Via Torino 20, Milano", "Via Torino 20, Milano")),
    ),
    (
        _pdf("Permesso di soggiorno", "Name: Ada Lovelace", "Via Padova 10, Milano"),
        _open(
            "permit",
            _linked("Ada Lovelace", "Name: Ada Lovelace"),
            _linked("Via Padova 10, Milano", "Via Padova 10, Milano"),
        ),
    ),
    (
        _pdf("Dichiarazione di residenza", "Name: Ada Lovelace", "Via Torino 20, Milano"),
        _open("unknown"),
    ),
    (
        _pdf("Lease agreement", "Passport", "Name: Ada Lovelace", "Via Torino 20, Milano"),
        _open("ambiguous"),
    ),
    (b"%PDF-1.4\n%%EOF", _open("unknown")),
    (_png(), _open("unknown")),
)


def test_each_fixture_keeps_its_line_or_stays_unavailable():
    for payload, expected in FIXTURES:
        found = fields(payload)
        assert found == expected
        assert "01/11/2026" not in (found["name"]["value"], found["address"]["value"])
