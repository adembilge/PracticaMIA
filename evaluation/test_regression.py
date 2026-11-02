"""The pinned citation and rule result stay put. A drift fails."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from regression import load, measure


def test_the_live_result_matches_the_version():
    assert measure() == load()


def test_a_drift_does_not_match_the_version():
    found = json.loads(json.dumps(measure()))
    found["retrieval"][0]["passage_id"] = "p-other"
    assert found != load()
    found = json.loads(json.dumps(measure()))
    found["rules"][0]["result"]["decision"] = "no case"
    assert found != load()
    found = json.loads(json.dumps(measure()))
    found["embedding"] = "0"
    assert found != load()
    found = json.loads(json.dumps(measure()))
    found["status_rejected"] = False
    assert found != load()
