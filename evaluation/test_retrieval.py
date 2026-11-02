"""Deterministic retrieval checks. No network and no database."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "evaluation"))

import pytest
from embeddings import embed

import ragcheck


def _embedder(data, extra=()):
    texts = [passage["text"] for passage in data["passages"]]
    texts.extend(query["text"] for query in data["queries"])
    texts.extend(extra)
    return ragcheck.MockEmbedder({text: embed(text) for text in texts})


def test_fixture_returns_expected_citation():
    data = ragcheck.load()
    query = data["queries"][0]
    embedder = _embedder(data)
    hit = ragcheck.rank(query, data["passages"], embedder)
    assert hit["passage_id"] == query["expect"]
    assert hit["citation"]["passage_id"] == hit["passage_id"]
    assert hit["citation"]["source_id"] == "src-alpha"
    assert "alpha token elsewhere" not in embedder.calls


def test_other_jurisdiction_returns_no_hit():
    data = ragcheck.load()
    query = dict(data["queries"][0])
    query["jurisdiction"] = "nowhere"
    hit = ragcheck.rank(query, data["passages"], _embedder(data, (query["text"],)))
    assert hit is None


def test_promoted_status_rejected():
    passage = dict(ragcheck.load()["passages"][0])
    passage["review_status"] = "approved"
    with pytest.raises(ValueError):
        ragcheck.validate(passage)


def test_credential_key_rejected():
    passage = dict(ragcheck.load()["passages"][0])
    passage["password"] = "x"
    with pytest.raises(ValueError):
        ragcheck.validate(passage)
