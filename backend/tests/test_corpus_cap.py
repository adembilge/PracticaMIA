from ingest.__main__ import main, run_batch
from ingest.fetch import FetchResult
from ingest.models import SourceSpec
from ingest.upsert import finish_source, upsert_document
from test_embed_prefix import FakeEmbedder
from test_upsert import CountingEmbedder, FakeStore, _long_text, _source


class CapFakeStore(FakeStore):
    def __init__(self) -> None:
        super().__init__()
        self.chunk_writes = 0

    def replace_chunks(self, document_id: str, rows: list[dict]) -> None:
        self.chunk_writes += len(rows)
        super().replace_chunks(document_id, rows)


def test_cap_skips_insert():
    source = _source()
    url = "https://example.com/page"
    text = _long_text()
    store = CapFakeStore()
    embedder = CountingEmbedder()

    result = upsert_document(
        source,
        url,
        "Titolo",
        text,
        embedder,
        store,
        count_chunks=lambda: 40000,
    )

    assert result == "skipped"
    assert store.chunk_writes == 0
    assert embedder.embed_passages_calls == 0


def test_finish_source_corpus_cap_error():
    store = FakeStore()
    finish_source("src-1", ["skipped", "skipped"], ["corpus cap"], store)
    row = store.source_updates[-1]
    assert row["status"] == "error"
    assert row["error"] == "corpus cap"


def test_short_text_not_labeled_corpus_cap():
    source = _source()
    short = " ".join(["word"] * 10)
    store = CapFakeStore()
    result = upsert_document(
        source,
        "https://example.com/short",
        "Breve",
        short,
        CountingEmbedder(),
        store,
        count_chunks=lambda: 40000,
    )
    assert result == "skipped"


def _html_fixture() -> bytes:
    words = " ".join(["parola"] * 250)
    return (
        "<!DOCTYPE html><html><head><title>Titolo</title></head>"
        f"<body><p>{words}</p></body></html>"
    ).encode()


class ChunkCountStore:
    def __init__(self, chunk_count: int) -> None:
        self._chunk_count = chunk_count
        self.source_updates: list[dict] = []

    def count_chunks(self) -> int:
        return self._chunk_count

    def ensure_source(self, source: SourceSpec) -> None:
        pass

    def find_document(self, url: str) -> dict | None:
        return None

    def insert_document(self, **fields) -> str:
        return "doc-1"

    def delete_chunks(self, document_id: str) -> None:
        pass

    def has_chunks(self, document_id: str) -> bool:
        return False

    def replace_chunks(self, document_id: str, rows: list[dict]) -> None:
        pass

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


def test_run_batch_corpus_cap_skips_embed(monkeypatch, capsys):
    source = SourceSpec(
        id="src-cap",
        topic="immigrazione",
        name="Cap",
        batch="a",
        portal_url="https://example.com",
        urls=["https://example.com/page"],
        keywords=[],
        max_pages=30,
    )
    monkeypatch.setattr("ingest.__main__.load_sources", lambda _batch: [source])

    store = ChunkCountStore(40000)

    def fetch(url: str) -> FetchResult:
        return FetchResult(
            url=url,
            status=200,
            content_type="text/html",
            body=_html_fixture(),
            skipped_reason=None,
        )

    embedder = CountingEmbedder()
    assert run_batch("a", fetch, embedder, store) == 0
    assert embedder.embed_passages_calls == 0
    assert store.source_updates[-1]["error"] == "corpus cap"


def test_main_chunk_count_exit_code(monkeypatch, capsys):
    class StubStore:
        def __init__(self, n: int) -> None:
            self._n = n

        def count_chunks(self) -> int:
            return self._n

    def make_main_test(n: int) -> int:
        store = StubStore(n)

        monkeypatch.setattr("ingest.__main__.get_supabase", lambda: object())
        monkeypatch.setattr("ingest.__main__.SupabaseIngestStore", lambda _c: store)
        monkeypatch.setattr("ingest.__main__.Embedder", FakeEmbedder)
        monkeypatch.setattr("ingest.__main__.run_batch", lambda *a, **k: 0)

        code = main(["run", "--batch", "a"])
        out = capsys.readouterr().out.strip().splitlines()
        assert out[-1] == f"chunk_count={n}"
        return code

    assert make_main_test(40000) == 0
    assert make_main_test(40001) == 1