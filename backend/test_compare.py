"""Matching, missing, and contradictory papers."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from compare import compare

MATCH = (
    {"type": "lease", "name": "Ada Lovelace", "address": "Via Torino 20, Milano"},
    {"type": "identity", "name": "ada  lovelace", "address": None},
    {"type": "permit", "name": "Ada Lovelace", "address": "via torino 20 milano"},
)
STATED = "Via Torino 20, Milano"


def test_s01_names_and_addresses_match():
    found = compare(MATCH, STATED)
    assert found["name"]["status"] == "match"
    assert found["name"]["absent"] == []
    assert found["address"]["status"] == "match"
    assert found["address"]["absent"] == []
    assert found["address"]["values"] == [
        {"type": "lease", "value": "Via Torino 20, Milano"},
        {"type": "permit", "value": "via torino 20 milano"},
        {"type": "stated", "value": "Via Torino 20, Milano"},
    ]


def test_an_unknown_paper_is_ignored():
    extra = MATCH + (
        {"type": "unknown", "name": "Other Person", "address": "Via Dante 1"},
    )
    assert compare(extra, STATED) == compare(MATCH, STATED)


def test_a_missing_title_address_is_missing():
    found = compare(
        ({"type": "ownership", "name": "Ada Lovelace", "address": None},)
    )
    assert found["name"]["status"] == "match"
    assert found["address"]["status"] == "missing"
    assert found["address"]["absent"] == ["ownership"]
    assert found["address"]["values"] == []


def test_i02_shows_both_mismatches_and_picks_neither():
    found = compare(
        (
            {"type": "lease", "name": "Ada Lovlace", "address": "Via Torino 20"},
            {"type": "identity", "name": "Ada Lovelace", "address": None},
            {"type": "permit", "name": "Ada Lovlace", "address": "Via Padova 10"},
        )
    )
    assert found["name"]["status"] == "conflict"
    assert found["name"]["values"] == [
        {"type": "lease", "value": "Ada Lovlace"},
        {"type": "identity", "value": "Ada Lovelace"},
        {"type": "permit", "value": "Ada Lovlace"},
    ]
    assert found["address"]["status"] == "conflict"
    assert found["address"]["values"] == [
        {"type": "lease", "value": "Via Torino 20"},
        {"type": "permit", "value": "Via Padova 10"},
    ]
    assert "stop" not in found
    assert "chosen" not in found
