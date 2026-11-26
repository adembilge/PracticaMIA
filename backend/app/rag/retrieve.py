from typing import Literal

from app.rag.topics import GENERAL_PORTAL, TOPICS

TOPIC_COSINE_THRESHOLD = 0.45

_PORTAL_EN = (
    "The indexed official pages do not state this. Start from {portal_name}: {portal_url}"
)
_PORTAL_IT = (
    "Le pagine ufficiali indicizzate non lo riportano. Parti da {portal_name}: {portal_url}"
)


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def route_topic(query_embedding: list[float], profiles: list[dict]) -> str:
    """Returns a topic id or 'genel'."""
    best_topic = "genel"
    best_score = -1.0
    for profile in profiles:
        score = cosine(query_embedding, profile["embedding"])
        if score > best_score:
            best_score = score
            best_topic = profile["topic"]
    if best_score < TOPIC_COSINE_THRESHOLD:
        return "genel"
    return best_topic


def retrieve_chunks(query: str, topic: str, embedder, rpc) -> list[dict]:
    """Keys: id, content, heading, url, title, topic, fetched_at, cosine_similarity."""
    embedding = embedder.embed_query(query)
    topic_filter = "" if topic == "genel" else topic

    def call(text: str, filt: str) -> list[dict]:
        return rpc(embedding, text, filt, 4)

    try:
        rows = call(query, topic_filter)
    except Exception:
        short = " ".join(query.split()[:12])
        try:
            rows = call(short, topic_filter)
        except Exception:
            return []

    if not rows and topic != "genel":
        try:
            rows = call(query, "")
        except Exception:
            short = " ".join(query.split()[:12])
            try:
                rows = call(short, "")
            except Exception:
                return []

    for row in rows:
        row["cosine_similarity"] = float(row["cosine_similarity"])
    return rows


def portal_reply(topic: str, language: Literal["en", "it"]) -> tuple[str, list[dict]]:
    """Citation chunk_id is ''."""
    profile = TOPICS.get(topic, GENERAL_PORTAL)
    template = _PORTAL_EN if language == "en" else _PORTAL_IT
    text = template.format(
        portal_name=profile.portal_name,
        portal_url=profile.portal_url,
    )
    cites = [
        {
            "chunk_id": "",
            "title": profile.portal_name,
            "url": profile.portal_url,
            "heading": "",
            "fetched_at": "",
        }
    ]
    return text, cites