"""Pin the current retrieval citation and rule result. A drift fails the check."""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "backend"))
sys.path.insert(0, str(HERE))

from embeddings import embed
from rules import evaluate

import ragcheck

FIXTURE = HERE / "fixtures" / "regression.json"


def load():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _digest(vector):
    return hashlib.sha256(repr(vector).encode()).hexdigest()


def _embedder(data):
    texts = [passage["text"] for passage in data["passages"]]
    texts.extend(row["text"] for row in load()["retrieval"])
    return ragcheck.MockEmbedder({text: embed(text) for text in texts})


def _hit(query, passages, embedder):
    hit = ragcheck.rank(query, passages, embedder)
    row = {
        "text": query["text"],
        "jurisdiction": query["jurisdiction"],
        "procedure": query["procedure"],
        "passage_id": None,
        "source_id": None,
        "section": None,
        "source_version": None,
    }
    if hit is None:
        return row
    winner = next(passage for passage in passages if passage["id"] == hit["passage_id"])
    row["passage_id"] = hit["passage_id"]
    row["source_id"] = hit["citation"]["source_id"]
    row["section"] = hit["citation"]["section"]
    row["source_version"] = winner["source_version"]
    return row


def _rejected():
    passage = dict(ragcheck.load()["passages"][0])
    passage["review_status"] = "approved"
    try:
        ragcheck.validate(passage)
    except ValueError:
        return True
    return False


def measure():
    pinned = load()
    data = ragcheck.load()
    embedder = _embedder(data)
    retrieval = [
        _hit(
            {"text": row["text"], "jurisdiction": row["jurisdiction"], "procedure": row["procedure"]},
            data["passages"],
            embedder,
        )
        for row in pinned["retrieval"]
    ]
    rules = [{"facts": row["facts"], "result": evaluate(row["facts"])} for row in pinned["rules"]]
    return {
        "version": pinned["version"],
        "embedding": _digest(embed("alpha token")),
        "status_rejected": _rejected(),
        "retrieval": retrieval,
        "rules": rules,
    }
