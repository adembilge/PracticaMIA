"""A ready package carries the link. A conflict does not."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from prepare import LINK, prepare

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


def test_s01_package_uses_the_stated_address():
    found = prepare(S01, MATCH)
    assert found["ready"] is True
    assert found["missing"] == []
    assert found["name"] == "Ada Lovelace"
    assert found["address"] == "Via Torino 20, Milano"
    assert found["link"] == LINK
    corrected = prepare(
        S01,
        MATCH,
        {"name": "Other Person", "address": "Via Dante 1, Milano"},
    )
    assert corrected["name"] == "Ada Lovelace"
    assert corrected["address"] == "Via Torino 20, Milano"


def test_a_missing_title_paper_has_no_link():
    facts = dict(S01)
    facts["f07"] = "missing"
    found = prepare(facts, ())
    assert found["ready"] is False
    assert found["link"] is None
    assert found["name"] is None
    assert found["missing"] == ["f07"]


def test_an_unreadable_identity_paper_has_no_link():
    facts = dict(S01)
    facts["f08"] = "unreadable"
    found = prepare(facts, MATCH)
    assert found["ready"] is False
    assert found["link"] is None


def test_i02_stays_blocked_until_both_values_are_named():
    facts = dict(S01)
    facts["named"] = True
    before = dict(facts)
    found = prepare(facts, CONFLICT)
    assert found["ready"] is False
    assert found["link"] is None
    assert found["missing"] == ["f09"]
    assert found["warnings"]["name"]["values"] == [
        {"type": "lease", "value": "Ada Lovlace"},
        {"type": "identity", "value": "Ada Lovelace"},
        {"type": "permit", "value": "Ada Lovlace"},
    ]
    assert found["warnings"]["address"]["values"] == [
        {"type": "lease", "value": "Via Torino 20"},
        {"type": "permit", "value": "Via Padova 10"},
        {"type": "stated", "value": "Via Torino 20, Milano"},
    ]
    assert facts == before
    named = prepare(
        S01,
        CONFLICT,
        {"name": "Ada Lovelace", "address": "Via Torino 20, Milano"},
    )
    assert named["ready"] is True
    assert named["name"] == "Ada Lovelace"
    assert named["address"] == "Via Torino 20, Milano"
    assert named["link"] == LINK


def test_s02_package_keeps_the_entered_address():
    facts = {
        "language": "Italian",
        "f04": "via Savona 12, Milano",
        "f05": "Owner",
        "f07": "read",
    }
    papers = (
        {"type": "ownership", "name": "Ada Lovelace", "address": "via Savona 12, Milano"},
    )
    found = prepare(facts, papers)
    assert found["ready"] is True
    assert found["address"] == "via Savona 12, Milano"
