from unittest.mock import patch

from app.agent.graph import build_graph

CHUNK = {
    "id": "known",
    "content": "Il rinnovo si chiede in Questura.",
    "heading": "Rinnovo",
    "url": "https://www.poliziadistato.it/articolo/225",
    "title": "Permesso",
    "topic": "immigrazione",
    "fetched_at": "2026-11-01T00:00:00+00:00",
    "cosine_similarity": 0.8,
}

PROFILES = [{"topic": "immigrazione", "embedding": [1.0, 0.0]}]

UNSUPPORTED_ANSWER = (
    "PracticaMIA answers in English and Italian. "
    "Ask your question again in one of those languages."
)


class FakeEmbedder:
    def __init__(self, vector: list[float] | None = None) -> None:
        self.vector = vector or [0.9, 0.1]
        self.queries: list[str] = []

    def embed_query(self, query: str) -> list[float]:
        self.queries.append(query)
        return self.vector


class ChunkRpc:
    def __init__(self) -> None:
        self.count = 0
        self.queries: list[str] = []

    def __call__(self, embedding, query_text, topic_filter, match_count):
        self.count += 1
        self.queries.append(query_text)
        return [CHUNK]


class EmptyRpc:
    def __init__(self) -> None:
        self.count = 0

    def __call__(self, embedding, query_text, topic_filter, match_count):
        self.count += 1
        return []


class RecordingComplete:
    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.count = 0

    def __call__(self, messages: list[dict]) -> str:
        self.count += 1
        if self.count > len(self.responses):
            raise RuntimeError(
                f"RecordingComplete exhausted: call {self.count}, "
                f"only {len(self.responses)} scripted response(s)"
            )
        return self.responses[self.count - 1]


def _invoke(graph, question: str) -> dict:
    return graph.invoke({"question": question, "history": []})


def test_graph_refine_triggers_second_retrieval():
    rpc = ChunkRpc()
    complete = RecordingComplete(
        [
            "Testo.\nCITATIONS: known\nREFINE: rinnovo permesso",
            "Testo finale.\nCITATIONS: known",
        ]
    )
    graph = build_graph(FakeEmbedder(), complete, PROFILES, rpc)
    result = _invoke(graph, "Come rinnovo il permesso di soggiorno?")

    assert complete.count == 2
    assert rpc.count == 2
    assert rpc.queries[1] == "rinnovo permesso"
    assert result.get("refined_query") is None
    assert result["answer"] == "Testo finale."
    assert result["citations"][0]["url"].endswith("/225")
    assert result["insufficient"] is False


def test_graph_ignores_refine_after_second_retrieval():
    rpc = ChunkRpc()
    complete = RecordingComplete(
        [
            "Testo.\nCITATIONS: known\nREFINE: rinnovo permesso",
            "Testo finale.\nCITATIONS: known\nREFINE: altra query",
        ]
    )
    graph = build_graph(FakeEmbedder(), complete, PROFILES, rpc)
    result = _invoke(graph, "Come rinnovo il permesso di soggiorno?")

    assert complete.count == 2
    assert rpc.count == 2
    assert rpc.queries[1] == "rinnovo permesso"
    assert result.get("refined_query") is None
    assert result["answer"] == "Testo finale."
    assert result["citations"][0]["url"].endswith("/225")
    assert result["insufficient"] is False


def test_graph_single_pass_without_refine():
    rpc = ChunkRpc()
    complete = RecordingComplete(["Testo.\nCITATIONS: known"])
    graph = build_graph(FakeEmbedder(), complete, PROFILES, rpc)
    result = _invoke(graph, "Come rinnovo il permesso di soggiorno?")

    assert complete.count == 1
    assert rpc.count == 1
    assert result["answer"] == "Testo."
    assert result["citations"][0]["url"].endswith("/225")
    assert result["insufficient"] is False


def test_graph_empty_chunks_uses_portal_reply():
    rpc = EmptyRpc()
    complete = RecordingComplete([])
    graph = build_graph(FakeEmbedder(), complete, PROFILES, rpc)
    result = _invoke(graph, "Come rinnovo il permesso di soggiorno?")

    assert complete.count == 0
    assert "https://www.poliziadistato.it/articolo/225" in result["answer"]
    assert result["insufficient"] is True


def test_graph_unsupported_language_skips_llm():
    rpc = ChunkRpc()
    complete = RecordingComplete([])
    with patch("app.rag.language._top_lang", return_value=("tr", 0.99)):
        graph = build_graph(FakeEmbedder(), complete, PROFILES, rpc)
        result = _invoke(graph, "Oturum iznimi nasıl yenilerim?")

    assert complete.count == 0
    assert rpc.count == 0
    assert result["answer"].startswith("PracticaMIA answers in English and Italian.")
    assert result["answer"] == UNSUPPORTED_ANSWER
    assert result["insufficient"] is True
    assert result["citations"] == []