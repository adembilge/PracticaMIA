from ingest.__main__ import main, run_batch
from ingest.fetch import FetchResult
from ingest.models import SourceSpec
from test_embed_prefix import FakeEmbedder


def _html_fixture() -> bytes:
    words = " ".join(["parola"] * 250)
    return (
        "<!DOCTYPE html><html><head><title>Titolo ufficiale</title></head>"
        f"<body><p>{words}</p></body></html>"
    ).encode()


def _source(source_id: str = "src-test", url: str = "https://www.poliziadistato.it/articolo/225") -> SourceSpec:
    return SourceSpec(
        id=source_id,
        topic="immigrazione",
        name="Test source",
        batch="a",
        portal_url=url,
        urls=[url],
        keywords=["permesso"],
        max_pages=30,
    )


class CountingEmbedder:
    def __init__(self) -> None:
        self.embed_passages_calls = 0
        self._inner = FakeEmbedder()

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        self.embed_passages_calls += 1
        return self._inner.embed_passages(texts)


class MemoryIngestStore:
    def __init__(self) -> None:
        self._next_id = 1
        self.documents_by_url: dict[str, dict] = {}
        self.chunks_by_doc_id: dict[str, list[dict]] = {}
        self.sources: dict[str, dict] = {}
        self.source_updates: list[dict] = []

    def ensure_source(self, source: SourceSpec) -> None:
        self.sources[source.id] = {
            "id": source.id,
            "topic": source.topic,
            "name": source.name,
            "batch": source.batch,
            "portal_url": source.portal_url,
        }

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
        self.chunks_by_doc_id.pop(document_id, None)

    def has_chunks(self, document_id: str) -> bool:
        return bool(self.chunks_by_doc_id.get(document_id))

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

    def count_chunks(self) -> int:
        return sum(len(rows) for rows in self.chunks_by_doc_id.values())


def _ok_fetch(body: bytes | None = None):
    payload = body if body is not None else _html_fixture()

    def fetch(url: str) -> FetchResult:
        return FetchResult(
            url=url,
            status=200,
            content_type="text/html",
            body=payload,
            skipped_reason=None,
        )

    return fetch


def test_run_batch_second_pass_unchanged(monkeypatch, capsys):
    source = _source()
    monkeypatch.setattr("ingest.__main__.load_sources", lambda _batch: [source])

    store = MemoryIngestStore()
    embedder = CountingEmbedder()
    fetch = _ok_fetch()

    assert run_batch("a", fetch, embedder, store) == 0
    assert len(store.documents_by_url) == 1
    doc_id = next(iter(store.documents_by_url.values()))["id"]
    chunks = store.chunks_by_doc_id[doc_id]
    assert len(chunks) >= 1
    assert all(len(row["embedding"]) == 384 for row in chunks)
    calls_after_first = embedder.embed_passages_calls
    assert calls_after_first >= 1

    first_line = capsys.readouterr().out.strip().splitlines()[-1]
    assert "inserted=1" in first_line
    assert "unchanged=0" in first_line

    assert run_batch("a", fetch, embedder, store) == 0
    assert embedder.embed_passages_calls == calls_after_first

    second_line = capsys.readouterr().out.strip().splitlines()[-1]
    assert "unchanged=1" in second_line


def test_run_batch_continues_after_source_exception(monkeypatch, capsys):
    url_ok = "https://www.poliziadistato.it/articolo/225"
    url_bad = "https://www.interno.gov.it/it/temi/immigrazione-e-asilo"
    source_bad = _source("src-bad", url_bad)
    source_ok = _source("src-ok", url_ok)
    monkeypatch.setattr("ingest.__main__.load_sources", lambda _batch: [source_bad, source_ok])

    body = _html_fixture()

    def fetch(url: str) -> FetchResult:
        if url == url_bad:
            raise RuntimeError("fetch failed")
        return FetchResult(
            url=url,
            status=200,
            content_type="text/html",
            body=body,
            skipped_reason=None,
        )

    store = MemoryIngestStore()
    code = run_batch("a", fetch, FakeEmbedder(), store)

    assert code == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("src-bad error")
    assert lines[1].startswith("src-ok ok")
    assert store.source_updates[0]["status"] == "error"
    assert store.source_updates[0]["error"] == "fetch failed"
    assert store.source_updates[1]["status"] == "ok"


def test_run_batch_robots_skip_returns_zero(monkeypatch, capsys):
    source = _source()
    monkeypatch.setattr("ingest.__main__.load_sources", lambda _batch: [source])

    def fetch(url: str) -> FetchResult:
        return FetchResult(
            url=url,
            status=0,
            content_type="",
            body=b"",
            skipped_reason="robots",
        )

    store = MemoryIngestStore()
    assert run_batch("a", fetch, FakeEmbedder(), store) == 0
    line = capsys.readouterr().out.strip()
    assert line.startswith("src-test error")
    assert "skipped=1" in line


def test_main_missing_supabase(capsys, monkeypatch):
    def fail_supabase():
        raise RuntimeError("supabase is not configured")

    monkeypatch.setattr("ingest.__main__.get_supabase", fail_supabase)
    code = main(["run", "--batch", "a"])
    assert code == 2
    assert capsys.readouterr().out.strip() == "supabase is not configured"


def test_main_requires_run_subcommand():
    assert main([]) == 2
    assert main(["crawl", "--batch", "a"]) == 2


def test_main_prints_error_to_stderr_on_failure(capsys, monkeypatch):
    class FailingEmbedder:
        def __init__(self) -> None:
            raise RuntimeError("db down")

    monkeypatch.setattr("ingest.__main__.get_supabase", lambda: object())
    monkeypatch.setattr("ingest.__main__.Embedder", FailingEmbedder)
    code = main(["run", "--batch", "a"])
    captured = capsys.readouterr()
    assert code == 1
    assert captured.err.strip() == "db down"
    assert captured.out == ""