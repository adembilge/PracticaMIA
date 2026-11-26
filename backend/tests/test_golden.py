from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from app.db import get_supabase
from app.rag.embed import Embedder
from app.rag.language import detect_language
from app.rag.retrieve import retrieve_chunks, route_topic
from app.rag.topics import TOPICS

GOLDEN_PATH = Path(__file__).parent / "golden" / "questions.jsonl"

with GOLDEN_PATH.open(encoding="utf-8") as _golden_file:
    GOLDEN_CASES = [json.loads(line) for line in _golden_file if line.strip()]


def _coerce_embedding(raw) -> list[float]:
    if isinstance(raw, list):
        return [float(x) for x in raw]
    if isinstance(raw, str):
        return [float(x) for x in json.loads(raw)]
    raise TypeError(f"unexpected embedding type: {type(raw)}")


def _hostname_ends_with(url: str, expected_host: str) -> bool:
    hostname = urlsplit(url or "").hostname
    if not hostname:
        return False
    return hostname.lower().endswith(expected_host.lower())


def _host_accepted(chunks: list, expected_host: str, topic: str) -> bool:
    portal_host = urlsplit(TOPICS[topic].portal_url).hostname or ""
    for chunk in chunks:
        url = chunk.get("url") or ""
        if _hostname_ends_with(url, expected_host):
            return True
        if portal_host and _hostname_ends_with(url, portal_host):
            return True
    return False


def _load_topic_profiles(client) -> list[dict]:
    profile_rows = client.table("topic_profiles").select("topic, embedding").execute().data or []
    return [
        {"topic": row["topic"], "embedding": _coerce_embedding(row["embedding"])}
        for row in profile_rows
    ]


def _make_rpc(client):
    def rpc(query_embedding_vec, query_text, topic_filter, match_count):
        result = client.rpc(
            "match_chunks",
            {
                "query_embedding": query_embedding_vec,
                "query_text": query_text,
                "topic_filter": topic_filter,
                "match_count": match_count,
            },
        ).execute()
        return result.data or []

    return rpc


@pytest.mark.integration
@pytest.mark.parametrize(
    "case",
    GOLDEN_CASES,
    ids=[f"{c['topic']}-{i}" for i, c in enumerate(GOLDEN_CASES)],
)
def test_golden_question(case):
    if not os.environ.get("RUN_INTEGRATION"):
        pytest.skip("RUN_INTEGRATION is not set")

    question = case["question"]
    expected_language = case["language"]
    expected_topic = case["topic"]
    expected_host = case["host"]

    language, uncertain = detect_language(question)
    assert language == expected_language
    assert uncertain is False

    client = get_supabase()
    embedder = Embedder()
    query_embedding = embedder.embed_query(question)
    profiles = _load_topic_profiles(client)
    topic = route_topic(query_embedding, profiles)
    assert topic == expected_topic

    rpc = _make_rpc(client)
    chunks = retrieve_chunks(question, topic, embedder, rpc)
    assert len(chunks) >= 1
    assert _host_accepted(chunks, expected_host, topic)