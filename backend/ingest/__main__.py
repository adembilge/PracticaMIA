import argparse
import sys
import time
from collections.abc import Callable
from typing import Literal
from urllib.robotparser import RobotFileParser

import httpx
from supabase import Client

from app.db import get_supabase
from app.rag.embed import Embedder
from ingest.catalog import load_sources
from ingest.discover import discover
from ingest.extract import extract_html, extract_pdf
from ingest.fetch import (
    MAX_REDIRECTS,
    TIMEOUT_SECONDS,
    USER_AGENT,
    FetchResult,
    fetch_url,
)
from ingest.models import SourceSpec
from ingest.upsert import finish_source, upsert_document


class SupabaseIngestStore:
    def __init__(self, client: Client) -> None:
        self._client = client

    def ensure_source(self, source: SourceSpec) -> None:
        self._client.table("sources").upsert(
            {
                "id": source.id,
                "topic": source.topic,
                "name": source.name,
                "batch": source.batch,
                "portal_url": source.portal_url,
            }
        ).execute()

    def find_document(self, url: str) -> dict | None:
        resp = (
            self._client.table("documents")
            .select("id, content_hash")
            .eq("url", url)
            .limit(1)
            .execute()
        )
        if not resp.data:
            return None
        return resp.data[0]

    def insert_document(
        self,
        *,
        source_id: str,
        url: str,
        title: str,
        topic: str,
        language: str,
        fetched_at: str,
        content_hash: str,
    ) -> str:
        resp = (
            self._client.table("documents")
            .upsert(
                {
                    "source_id": source_id,
                    "url": url,
                    "title": title,
                    "topic": topic,
                    "language": language,
                    "fetched_at": fetched_at,
                    "content_hash": content_hash,
                },
                on_conflict="url",
            )
            .select("id")
            .execute()
        )
        return resp.data[0]["id"]

    def delete_chunks(self, document_id: str) -> None:
        self._client.table("chunks").delete().eq("document_id", document_id).execute()

    def has_chunks(self, document_id: str) -> bool:
        resp = (
            self._client.table("chunks")
            .select("id")
            .eq("document_id", document_id)
            .limit(1)
            .execute()
        )
        return bool(resp.data)

    def replace_chunks(self, document_id: str, rows: list[dict]) -> None:
        payload = [
            {
                "document_id": document_id,
                "chunk_index": row["chunk_index"],
                "heading": row["heading"],
                "content": row["content"],
                "content_hash": row["content_hash"],
                "embedding": row["embedding"],
            }
            for row in rows
        ]
        if payload:
            self._client.table("chunks").insert(payload).execute()

    def update_source(
        self,
        source_id: str,
        *,
        status: str,
        error: str | None,
        last_crawled_at: str,
    ) -> None:
        self._client.table("sources").update(
            {
                "status": status,
                "error": error,
                "last_crawled_at": last_crawled_at,
            }
        ).eq("id", source_id).execute()


def _source_status(outcomes: list[str]) -> str:
    if any(item in ("inserted", "unchanged") for item in outcomes):
        return "ok"
    return "error"


def _outcome_tally(outcomes: list[str], label: str) -> int:
    return sum(1 for item in outcomes if item == label)


def run_batch(
    batch: Literal["a", "b", "c", "all"],
    fetch: Callable[[str], FetchResult],
    embedder,
    store,
) -> int:
    sources = load_sources(batch)
    for source in sources:
        outcomes: list[str] = []
        errors: list[str] = []
        try:
            store.ensure_source(source)
            queue = list(source.urls)
            seen: set[str] = set()
            while queue and len(seen) < source.max_pages:
                url = queue.pop(0)
                if url in seen:
                    continue
                seen.add(url)
                result = fetch(url)
                if result.skipped_reason or not result.body or result.status != 200:
                    outcomes.append("skipped")
                    continue

                media = result.content_type.casefold()
                if media == "application/pdf":
                    title, text = extract_pdf(result.body)
                elif media == "text/html":
                    title, text = extract_html(result.body, url)
                    decoded_html = result.body.decode("utf-8", errors="replace")
                    for link in discover(decoded_html, url, source, seen):
                        queue.append(link)
                else:
                    outcomes.append("skipped")
                    continue

                if not text.strip():
                    outcomes.append("skipped")
                    continue

                outcomes.append(
                    upsert_document(
                        source,
                        url,
                        title or "",
                        text,
                        embedder,
                        store,
                    )
                )
        except Exception as exc:
            errors.append(str(exc))

        finish_source(source.id, outcomes, errors, store)
        status = _source_status(outcomes)
        inserted = _outcome_tally(outcomes, "inserted")
        unchanged = _outcome_tally(outcomes, "unchanged")
        skipped = _outcome_tally(outcomes, "skipped")
        print(
            f"{source.id} {status} inserted={inserted} "
            f"unchanged={unchanged} skipped={skipped}"
        )
    return 0


def _build_fetch(client: httpx.Client) -> Callable[[str], FetchResult]:
    host_next: dict[str, float] = {}
    robots_cache: dict[str, RobotFileParser | None] = {}

    def robots_for(host: str) -> RobotFileParser | None:
        if host not in robots_cache:
            parser = RobotFileParser()
            robots_url = f"https://{host}/robots.txt"
            try:
                response = client.get(
                    robots_url,
                    headers={"User-Agent": USER_AGENT},
                    timeout=TIMEOUT_SECONDS,
                )
                if response.status_code == 200:
                    parser.parse(response.text.splitlines())
                    robots_cache[host] = parser
                else:
                    robots_cache[host] = None
            except Exception:
                robots_cache[host] = None
        return robots_cache[host]

    def fetch(url: str) -> FetchResult:
        return fetch_url(
            url,
            client,
            robots_for=robots_for,
            now=time.time,
            host_next=host_next,
            sleep=time.sleep,
        )

    return fetch


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run", nargs="?")
    parser.add_argument("--batch", default="a", choices=["a", "b", "c", "all"])
    args = parser.parse_args(argv)
    if args.run != "run":
        return 2
    try:
        client = get_supabase()
    except RuntimeError as exc:
        if str(exc) == "supabase is not configured":
            print("supabase is not configured")
            return 2
        raise
    try:
        store = SupabaseIngestStore(client)
        embedder = Embedder()
        with httpx.Client(
            follow_redirects=True,
            max_redirects=MAX_REDIRECTS,
        ) as http_client:
            fetch = _build_fetch(http_client)
            return run_batch(args.batch, fetch, embedder, store)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))