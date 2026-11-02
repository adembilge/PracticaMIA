"""A name is the label. A date stays as written."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract import read

BODY = (
    b"%PDF-1.4\n"
    b"(Name: Ada Lovelace) Tj\n"
    b"(Via Torino 20, Milano) Tj\n"
    b"(Date: 01/11/2026) Tj\n"
    b"%%EOF"
)
PROPOSAL = {"name": "Ada Lovelace", "address": "Via Torino 20, Milano"}


def _png():
    data = (1).to_bytes(4, "big") + (1).to_bytes(4, "big") + b"\x08\x02\x00\x00\x00"
    return b"\x89PNG\r\n\x1a\n" + len(data).to_bytes(4, "big") + b"IHDR" + data + b"\x00\x00\x00\x00"


def _jpeg():
    return (
        b"\xff\xd8\xff\xc0\x00\x0b\x08"
        + (1).to_bytes(2, "big")
        + (1).to_bytes(2, "big")
        + b"\x01\x01\x11\x00"
    )


def test_a_named_pdf_keeps_the_date():
    found = read(BODY)
    assert found["status"] == "read"
    assert found["name"] == "Ada Lovelace"
    assert found["address"] == "Via Torino 20, Milano"
    assert "01/11/2026" in found["pages"][0]["text"]
    assert found["pages"][0]["page"] == 1


def test_a_date_label_is_not_a_name():
    payload = (
        b"%PDF-1.4\n"
        b"(Name: 01/11/2026) Tj\n"
        b"(Via Torino 20, Milano) Tj\n"
        b"%%EOF"
    )
    found = read(payload)
    assert found["status"] == "unreadable"
    assert found["name"] is None
    assert "01/11/2026" in found["pages"][0]["text"]


def test_a_pdf_without_text_is_unreadable():
    found = read(b"%PDF-1.4\n%%EOF")
    assert found == {"status": "unreadable", "pages": [], "name": None, "address": None}


def test_an_image_stays_unreadable_until_both_strings_are_proposed():
    png = _png()
    jpeg = _jpeg()
    assert read(png)["status"] == "unreadable"
    assert read(jpeg)["status"] == "unreadable"
    assert read(png)["pages"] == []
    found = read(png, PROPOSAL)
    assert found["status"] == "read"
    assert found["name"] == "Ada Lovelace"
    assert found["address"] == "Via Torino 20, Milano"
    assert found["pages"] == []
    extra = dict(PROPOSAL)
    extra["date"] = "01/11/2026"
    assert read(png, extra)["status"] == "unreadable"
    assert read(png, {"name": "Ada Lovelace"})["status"] == "unreadable"
