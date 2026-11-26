from app.rag.retrieve import portal_reply, retrieve_chunks, route_topic


def test_route_picks_close_topic():
    profiles = [
        {"topic": "anagrafe", "embedding": [1.0, 0.0]},
        {"topic": "fisco", "embedding": [0.0, 1.0]},
    ]
    assert route_topic([0.9, 0.1], profiles) == "anagrafe"


def test_route_general_below_threshold():
    profiles = [{"topic": "anagrafe", "embedding": [1.0, 0.0]}]
    assert route_topic([0.0, 1.0], profiles) == "genel"


def test_route_general_empty_profiles():
    assert route_topic([1.0, 0.0], []) == "genel"


class FakeEmbedder:
    def __init__(self, vector: list[float] | None = None) -> None:
        self.vector = vector or [0.1, 0.2]
        self.queries: list[str] = []

    def embed_query(self, query: str) -> list[float]:
        self.queries.append(query)
        return self.vector


class RecordingRpc:
    def __init__(self, responses: list, *, raises_on: set[tuple[str, str]] | None = None) -> None:
        self.calls: list[tuple] = []
        self._responses = list(responses)
        self._raises_on = raises_on or set()
        self._call_index = 0

    def __call__(self, embedding, query_text, topic_filter, match_count):
        self.calls.append((embedding, query_text, topic_filter, match_count))
        key = (query_text, topic_filter)
        if key in self._raises_on:
            raise RuntimeError("rpc failed")
        if self._call_index < len(self._responses):
            row = self._responses[self._call_index]
            self._call_index += 1
            return row
        return []


def test_retrieve_genel_uses_empty_topic_filter_and_match_count_four():
    rpc = RecordingRpc([[]])
    embedder = FakeEmbedder()
    result = retrieve_chunks("Come cambio residenza?", "genel", embedder, rpc)
    assert result == []
    assert len(rpc.calls) == 1
    assert rpc.calls[0][2] == ""
    assert rpc.calls[0][3] == 4
    assert embedder.queries == ["Come cambio residenza?"]


def test_retrieve_specific_topic_then_broadens_when_empty():
    rpc = RecordingRpc([[], [{"id": "1", "cosine_similarity": "0.5"}]])
    embedder = FakeEmbedder()
    result = retrieve_chunks("tax question", "fisco", embedder, rpc)
    assert len(rpc.calls) == 2
    assert rpc.calls[0][2] == "fisco"
    assert rpc.calls[1][2] == ""
    assert rpc.calls[1][1] == "tax question"
    assert result[0]["cosine_similarity"] == 0.5


def test_retrieve_rpc_retry_short_query_on_exception():
    long_query = " ".join(f"word{i}" for i in range(20))
    short_query = " ".join(f"word{i}" for i in range(12))

    class SelectiveRpc:
        def __init__(self) -> None:
            self.calls: list[tuple] = []

        def __call__(self, embedding, query_text, topic_filter, match_count):
            self.calls.append((query_text, topic_filter, match_count))
            if query_text == long_query and topic_filter == "anagrafe":
                raise RuntimeError("rpc failed")
            return [{"id": "1", "cosine_similarity": "0.8"}]

    rpc = SelectiveRpc()
    embedder = FakeEmbedder()
    result = retrieve_chunks(long_query, "anagrafe", embedder, rpc)
    assert len(result) == 1
    assert len(rpc.calls) == 2
    assert rpc.calls[0][0] == long_query
    assert rpc.calls[1][0] == short_query
    assert rpc.calls[1][2] == 4


def test_retrieve_rpc_second_exception_returns_empty():
    rpc = RecordingRpc([], raises_on={("fail", "fisco"), ("fail", "")})
    embedder = FakeEmbedder()

    class AlwaysFailRpc:
        def __init__(self) -> None:
            self.calls = []

        def __call__(self, embedding, query_text, topic_filter, match_count):
            self.calls.append((query_text, topic_filter))
            raise RuntimeError("rpc failed")

    fail_rpc = AlwaysFailRpc()
    assert retrieve_chunks("fail", "fisco", embedder, fail_rpc) == []
    assert len(fail_rpc.calls) == 2
    assert fail_rpc.calls[1][0] == "fail"


def test_retrieve_keeps_low_similarity_rows():
    rpc = RecordingRpc([[{"id": "x", "cosine_similarity": "0.15"}]])
    embedder = FakeEmbedder()
    rows = retrieve_chunks("q", "sanita", embedder, rpc)
    assert rows[0]["cosine_similarity"] == 0.15
    assert isinstance(rows[0]["cosine_similarity"], float)


def test_portal_reply_english():
    text, cites = portal_reply("immigrazione", "en")
    assert "https://www.poliziadistato.it/articolo/225" in text
    assert (
        text
        == "The indexed official pages do not state this. Start from Polizia di Stato: https://www.poliziadistato.it/articolo/225"
    )
    assert cites[0]["chunk_id"] == ""
    assert cites[0]["fetched_at"] == ""
    assert cites[0]["title"] == "Polizia di Stato"
    assert cites[0]["url"] == "https://www.poliziadistato.it/articolo/225"
    assert cites[0]["heading"] == ""


def test_portal_reply_italian():
    text, cites = portal_reply("fisco", "it")
    assert (
        text
        == "Le pagine ufficiali indicizzate non lo riportano. Parti da Agenzia delle Entrate: https://www.agenziaentrate.gov.it/"
    )
    assert cites[0]["title"] == "Agenzia delle Entrate"


def test_portal_reply_general():
    text, _cites = portal_reply("genel", "it")
    assert "https://www.interno.gov.it/" in text


def test_portal_reply_unknown_topic_uses_general_portal():
    text, cites = portal_reply("nonexistent", "en")
    assert "https://www.interno.gov.it/" in text
    assert cites[0]["title"] == "Ministero dell'Interno"