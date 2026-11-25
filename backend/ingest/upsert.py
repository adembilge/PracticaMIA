import hashlib
from datetime import datetime, timezone
from typing import Literal


from ingest.chunk import chunk_text
from ingest.models import SourceSpec

Outcome = Literal["inserted", "unchanged", "skipped"]


def _content_hash(text: str) -> str:
    normalized = " ".join(text.split())
    return hashlib.sha256(normalized.encode()).hexdigest()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_document(
    source: SourceSpec,
    url: str,
    title: str,
    text: str,
    embedder,
    store,
) -> Outcome:
    if len(text.split()) < 200:
        return "skipped"

    content_hash = _content_hash(text)
    existing = store.find_document(url)
    if (
        existing is not None
        and existing["content_hash"] == content_hash
        and store.has_chunks(existing["id"])
    ):
        return "unchanged"

    existing_id = existing["id"] if existing is not None else None
    rows: list[dict] = []
    for chunk in chunk_text(text):
        vectors = embedder.embed_passages([chunk.content])
        if not vectors:
            continue
        rows.append(
            {
                "chunk_index": chunk.chunk_index,
                "heading": chunk.heading,
                "content": chunk.content,
                "content_hash": chunk.content_hash,
                "embedding": vectors[0],
            }
        )

    if existing_id is not None:
        store.delete_chunks(existing_id)

    document_id = store.insert_document(
        source_id=source.id,
        url=url,
        title=title,
        topic=source.topic,
        language="it",
        fetched_at=_utc_now_iso(),
        content_hash=content_hash,
    )
    try:
        store.replace_chunks(document_id, rows)
    except Exception:
        store.delete_chunks(document_id)
        raise
    return "inserted"


def finish_source(
    source_id: str,
    outcomes: list[str],
    errors: list[str],
    store,
) -> None:
    last_crawled_at = _utc_now_iso()
    if any(item in ("inserted", "unchanged") for item in outcomes):
        status = "ok"
        error = None
    else:
        status = "error"
        if errors:
            error = errors[0]
        elif outcomes:
            error = outcomes[0]
        else:
            error = "empty"

    store.update_source(
        source_id,
        status=status,
        error=error,
        last_crawled_at=last_crawled_at,
    )