"""Every synthetic file has one expected type."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from classify import classify


def _pdf(*lines):
    body = b"%PDF-1.4\n"
    for line in lines:
        body += b"(" + line.encode("latin-1") + b") Tj\n"
    return body + b"%%EOF"


def _png():
    data = (1).to_bytes(4, "big") + (1).to_bytes(4, "big") + b"\x08\x02\x00\x00\x00"
    return b"\x89PNG\r\n\x1a\n" + len(data).to_bytes(4, "big") + b"IHDR" + data + b"\x00\x00\x00\x00"


FIXTURES = (
    (_pdf("Lease agreement", "Name: Ada Lovelace"), "lease"),
    (_pdf("Atto di proprieta"), "ownership"),
    (_pdf("Passport"), "identity"),
    (_pdf("Permesso di soggiorno"), "permit"),
    (_pdf("Dichiarazione di residenza", "Name: Ada Lovelace"), "unknown"),
    (_pdf("Please send the file"), "unknown"),
    (_pdf("Lease agreement", "Passport"), "ambiguous"),
    (b"%PDF-1.4\n%%EOF", "unknown"),
    (_png(), "unknown"),
)


def test_each_fixture_has_its_type():
    found = [classify(payload)["type"] for payload, _expected in FIXTURES]
    assert found == [expected for _payload, expected in FIXTURES]
    assert "unknown" in found
    assert "ambiguous" in found
