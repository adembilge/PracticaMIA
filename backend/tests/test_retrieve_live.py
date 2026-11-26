import json
import os

import pytest

from app.db import get_supabase
from app.rag.embed import Embedder
from app.rag.retrieve import retrieve_chunks, route_topic

QUESTION = "Come cambio residenza?"


def _coerce_embedding(raw) -> list[float]:
    if isinstance(raw, list):
        return [float(x) for x in raw]
    if isinstance(raw, str):
        return [float(x) for x in json.loads(raw)]
    raise TypeError(f"unexpected embedding type: {type(raw)}")


@pytest.mark.integration
def test_retrieve_live_residenza():
    if not os.environ.get("RUN_INTEGRATION"):
        pytest.skip("RUN_INTEGRATION is not set")

    client = get_supabase()
    embedder = Embedder()
    query_embedding = embedder.embed_query(QUESTION)

    profile_rows = client.table("topic_profiles").select("topic, embedding").execute().data or []
    profiles = [
        {"topic": row["topic"], "embedding": _coerce_embedding(row["embedding"])}
        for row in profile_rows
    ]
    topic = route_topic(query_embedding, profiles)

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

    chunks = retrieve_chunks(QUESTION, topic, embedder, rpc)
    routed_anagrafe = topic == "anagrafe"
    url_hit = any("anagrafenazionale.interno.it" in (c.get("url") or "") for c in chunks)
    assert routed_anagrafe or url_hit