"""A line stays unconfirmed until the person names the value."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fields as fields_mod
from fields import fields
from review import agreed, confirm, review


def _pdf(*lines):
    body = b"%PDF-1.4\n"
    for line in lines:
        body += b"(" + line.encode("latin-1") + b") Tj\n"
    return body + b"%%EOF"


LEASE = _pdf(
    "Lease agreement",
    "Name: Ada Lovelace",
    "Via Torino 20, Milano",
    "Date: 01/11/2026",
)
PASSPORT = _pdf("Passport", "Via Torino 20, Milano")


def test_a_labeled_name_and_a_milano_line_are_not_agreed():
    found = review(fields(LEASE))
    assert found["name"]["review"] == "unverified"
    assert found["name"]["value"] == "Ada Lovelace"
    assert found["address"]["review"] == "flagged"
    assert found["address"]["raw"] == "Via Torino 20, Milano"
    assert agreed(found) == {"name": None, "address": None}
    assert "review" not in fields_mod.EMPTY


def test_the_person_can_correct_the_address():
    found = fields(LEASE)
    before = dict(found["address"])
    checked = confirm(found, "address", "Via Dante 1, Milano")
    assert checked["address"]["value"] == "Via Dante 1, Milano"
    assert checked["address"]["review"] == "verified"
    assert checked["address"]["raw"] == "Via Torino 20, Milano"
    assert checked["name"]["review"] == "unverified"
    assert agreed(checked) == {"name": None, "address": "Via Dante 1, Milano"}
    assert found["address"] == before


def test_a_confirmed_name_leaves_the_address_out():
    checked = confirm(fields(LEASE), "name", "  Ada Lovelace  ")
    assert checked["name"]["value"] == "Ada Lovelace"
    assert checked["name"]["review"] == "verified"
    assert checked["address"]["review"] == "flagged"
    assert agreed(checked) == {"name": "Ada Lovelace", "address": None}


def test_a_bad_confirmation_is_refused():
    found = fields(LEASE)
    before = {"name": dict(found["name"]), "address": dict(found["address"])}
    assert confirm(found, "date", "01/11/2026") is None
    assert confirm(found, "name", "  ") is None
    assert confirm(found, "name", None) is None
    assert found["name"] == before["name"]
    assert found["address"] == before["address"]


def test_a_missing_name_can_be_named():
    found = review(fields(PASSPORT))
    assert found["name"]["review"] == "unavailable"
    checked = confirm(found, "name", "Ada Lovelace")
    assert checked["name"]["review"] == "verified"
    assert checked["name"]["value"] == "Ada Lovelace"
    assert checked["name"]["page"] is None
    assert checked["name"]["raw"] is None
    assert agreed(checked) == {"name": "Ada Lovelace", "address": None}


def test_a_second_confirm_keeps_the_first_field():
    once = confirm(fields(LEASE), "name", "Ada Lovelace")
    twice = confirm(once, "address", "Via Dante 1, Milano")
    assert twice["name"]["review"] == "verified"
    assert twice["address"]["review"] == "verified"
    assert agreed(twice) == {"name": "Ada Lovelace", "address": "Via Dante 1, Milano"}
