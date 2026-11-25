import hashlib
import math
from datetime import datetime, timezone

from ingest.models import SourceSpec
from ingest.upsert import finish_source, upsert_document


class FakeEmbedder:
    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return [self._unit_vector() for _ in texts]

    @staticmethod
    def _unit_vector() -> list[float]:
        component = 1 / math.sqrt(384)
        return [component] * 384


class CountingEmbedder:
    def __init__(self) -> None:
        self.embed_passages_calls = 0
        self._inner = FakeEmbedder()

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        self.embed_passages_calls += 1
        return self._inner.embed_passages(texts)


def _source() -> SourceSpec:
    return SourceSpec(
        id="src-1",
        topic="immigrazione",
        name="Test",
        batch="a",
        portal_url="https://example.com",
        urls=["https://example.com"],
        keywords=[],
    )


def _long_text(extra: str = "") -> str:
    base = " ".join(["parola"] * 200)
    return f"{base} {extra}".strip()


def _doc_hash(text: str) -> str:
    return hashlib.sha256(" ".join(text.split()).encode()).hexdigest()


class FakeStore:
    def __init__(self) -> None:
        self._next_id = 1
        self.documents_by_url: dict[str, dict] = {}
        self.chunks_by_doc_id: dict[str, list[dict]] = {}
        self.source_updates: list[dict] = []
        self.delete_chunks_calls: list[str] = []

    def find_document(self, url: str) -> dict | None:
        doc = self.documents_by_url.get(url)
        if doc is None:
            return None
        return {"id": doc["id"], "content_hash": doc["content_hash"]}

    def insert_document(self, **fields) -> str:
        url = fields["url"]
        if url in self.documents_by_url:
            doc_id = self.documents_by_url[url]["id"]
            self.documents_by_url[url] = {**fields, "id": doc_id}
            return doc_id
        doc_id = f"doc-{self._next_id}"
        self._next_id += 1
        self.documents_by_url[url] = {**fields, "id": doc_id}
        return doc_id

    def delete_chunks(self, document_id: str) -> None:
        self.delete_chunks_calls.append(document_id)
        self.chunks_by_doc_id.pop(document_id, None)

    def replace_chunks(self, document_id: str, rows: list[dict]) -> None:
        self.chunks_by_doc_id[document_id] = list(rows)

    def update_source(
        self,
        source_id: str,
        *,
        status: str,
        error: str | None,
        last_crawled_at: str,
    ) -> None:
        self.source_updates.append(
            {
                "source_id": source_id,
                "status": status,
                "error": error,
                "last_crawled_at": last_crawled_at,
            }
        )


def test_unchanged_skips_embedding():
    source = _source()
    url = "https://example.com/page"
    text = _long_text()
    store = FakeStore()
    embedder = CountingEmbedder()

    first = upsert_document(source, url, "Titolo", text, embedder, store)
    calls_after_first = embedder.embed_passages_calls

    second = upsert_document(source, url, "Titolo", text, embedder, store)

    assert first == "inserted"
    assert second == "unchanged"
    assert embedder.embed_passages_calls == calls_after_first


def test_hash_change_deletes_old_chunks_and_inserts():
    source = _source()
    url = "https://example.com/page"
    text_v1 = _long_text()
    text_v2 = _long_text("aggiornato")
    assert _doc_hash(text_v1) != _doc_hash(text_v2)

    store = FakeStore()
    embedder = CountingEmbedder()

    upsert_document(source, url, "Titolo", text_v1, embedder, store)
    doc_id = store.documents_by_url[url]["id"]
    old_chunk_count = len(store.chunks_by_doc_id.get(doc_id, []))
    assert old_chunk_count >= 1

    outcome = upsert_document(source, url, "Titolo", text_v2, embedder, store)

    assert outcome == "inserted"
    assert doc_id in store.delete_chunks_calls
    assert store.documents_by_url[url]["content_hash"] == _doc_hash(text_v2)
    new_chunks = store.chunks_by_doc_id[doc_id]
    assert len(new_chunks) >= 1
    for row in new_chunks:
        assert "chunk_index" in row
        assert "heading" in row
        assert "content" in row
        assert "content_hash" in row
        assert "embedding" in row
        assert len(row["embedding"]) == 384


def test_short_text_skipped():
    source = _source()
    url = "https://example.com/short"
    text = " ".join(["word"] * 10)
    store = FakeStore()
    embedder = CountingEmbedder()

    outcome = upsert_document(source, url, "Breve", text, embedder, store)

    assert outcome == "skipped"
    assert embedder.embed_passages_calls == 0
    assert store.documents_by_url == {}
    assert store.chunks_by_doc_id == {}


def test_finish_source_ok_when_inserted_or_unchanged():
    store = FakeStore()
    finish_source("src-1", ["inserted", "skipped"], ["ignored"], store)
    assert store.source_updates[-1]["status"] == "ok"
    assert store.source_updates[-1]["error"] is None
    assert store.source_updates[-1]["last_crawled_at"].endswith("+00:00") or "T" in store.source_updates[-1]["last_crawled_at"]


def test_finish_source_error_when_all_skipped():
    store = FakeStore()
    finish_source("src-1", ["skipped", "skipped"], ["first-error", "second"], store)
    row = store.source_updates[-1]
    assert row["status"] == "error"
    assert row["error"] == "first-error"


def test_finish_source_error_when_outcomes_empty():
    store = FakeStore()
    before = datetime.now(timezone.utc).isoformat()
    finish_source("src-1", [], [], store)
    row = store.source_updates[-1]
    assert row["status"] == "error"
    assert row["error"] == "empty"
    assert row["last_crawled_at"] >= before