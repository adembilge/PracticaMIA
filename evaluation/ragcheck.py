"""Rank synthetic passages with a caller-supplied embedder."""
import json
from pathlib import Path

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "passages.json"
FIELDS = (
    "id",
    "text",
    "source_id",
    "source_version",
    "section",
    "jurisdiction",
    "procedure",
    "language",
    "review_status",
)
CREDENTIALS = frozenset(("password", "secret", "credential"))


class MockEmbedder:
    def __init__(self, mapping):
        self.mapping = mapping
        self.calls = []

    def embed(self, text):
        self.calls.append(text)
        if text not in self.mapping:
            raise KeyError(text)
        return self.mapping[text]


def load(path=FIXTURE):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for passage in data["passages"]:
        validate(passage)
    return data


def validate(passage):
    missing = [field for field in FIELDS if field not in passage]
    if missing:
        raise ValueError("missing fields: " + ", ".join(missing))
    if passage["review_status"] != "unreviewed":
        raise ValueError("review status is %s" % passage["review_status"])
    bad = [key for key in passage if key.lower() in CREDENTIALS]
    if bad:
        raise ValueError("credential field: " + ", ".join(bad))


def _cosine(left, right):
    return sum(a * b for a, b in zip(left, right))


def rank(query, passages, embedder):
    for passage in passages:
        validate(passage)
    kept = [
        passage
        for passage in passages
        if passage["jurisdiction"] == query["jurisdiction"]
        and passage["procedure"] == query["procedure"]
    ]
    if not kept:
        return None
    query_vector = embedder.embed(query["text"])
    scored = [
        (_cosine(query_vector, embedder.embed(passage["text"])), passage)
        for passage in kept
    ]
    scored.sort(key=lambda item: item[0], reverse=True)
    if scored[0][0] <= 0.0:
        return None
    winner = scored[0][1]
    return {
        "passage_id": winner["id"],
        "citation": {
            "source_id": winner["source_id"],
            "passage_id": winner["id"],
            "section": winner["section"],
        },
    }
