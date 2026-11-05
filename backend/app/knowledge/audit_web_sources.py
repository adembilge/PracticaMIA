"""One-pass audit and capture of registered original municipal HTML bytes.

Runs on operator-authorized network environments only; no redirects, no
retrieval bypasses, no authentication, proxies, retries, content synthesis,
source approval, database changes or external AI. All 14 curated webpage
URLs are attempted once. A successful original HTTP 200 response is copied
byte-for-byte to an artifact with its SHA-256 and extraction metadata.

Run from backend/:
  python -m app.knowledge.audit_web_sources --output-dir /tmp/official-audit

Only returned 200 OK original bytes with supported MIME and extractable text
are saved. HTTP 403, redirects, network failures and invalid media are explicit
failures; the JSON report records them individually.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from time import sleep
from typing import Any

from app.knowledge.acquisition import fetch_official_html
from app.knowledge.catalog import candidate_sources
from app.knowledge.document_extraction import extract_document


def _safe_error(exc: Exception) -> str:
    """Avoid persisting error bodies, headers, tokens or stack traces."""
    message = str(exc)
    if isinstance(exc, ValueError):
        if "HTTP " in message:
            return message.split("HTTP ", 1)[-1].split()[0].strip()[:3].join(
                ["HTTP ", ""]
            )
        if "redirect" in message.lower():
            return "redirect_not_followed"
        if "media type" in message.lower():
            return "unsupported_media_type"
        if "size limit" in message.lower():
            return "response_too_large"
        if "empty" in message.lower():
            return "empty_response"
        return "invalid_source_content"
    return "network_or_transport_error"


def audit_sources(
    output_dir: Path, *,
    sources: list[dict[str, str]] | None = None,
    transport: Any = None,
    delay_seconds: float = 0.0,
) -> dict[str, Any]:
    """Acquire 14 registered HTML originals, never from search snippets.

    The runner should use an isolated empty output directory. No DB access or
    secrets are used. We never follow HTTP redirects or retry blocked URLs.
    """
    selected = [
        item for item in (candidate_sources() if sources is None else sources)
        if item["document_type"] != "official_document"
    ]
    if len({item["id"] for item in selected}) != len(selected):
        raise ValueError("Duplicate candidate source identifiers")
    if output_dir.is_symlink():
        raise ValueError("Audit output cannot be a symlink")
    originals = output_dir / "originals"
    originals.mkdir(parents=True, exist_ok=True)
    if originals.is_symlink():
        raise ValueError("Originals output cannot be a symlink")
    rows = []
    for number, source in enumerate(selected):
        if number and delay_seconds:
            sleep(delay_seconds)
        row: dict[str, Any] = {
            "source_id": source["id"],
            "registered_url": source["official_url"],
            "result": "unavailable",
        }
        try:
            original, media = fetch_official_html(
                source["official_url"], transport=transport,
            )
            extracted, _ = extract_document(original, media)
            file = originals / (source["id"] + ".html")
            if file.is_symlink() or file.exists():
                raise ValueError("Destination exists or links outside audit directory")
            file.write_bytes(original)
            row.update({
                "result": "original_captured",
                "file": "originals/" + file.name,
                "media_type": media,
                "sha256": sha256(original).hexdigest(),
                "size_bytes": len(original),
                "passage_count": len(extracted.passages),
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as exc:
            row["reason"] = _safe_error(exc)
        rows.append(row)
        print(source["id"] + ": " + row["result"] +
              (" (" + row["reason"] + ")" if "reason" in row else ""),
              flush=True)
    report = {
        "audit_time_utc": datetime.now(timezone.utc).isoformat(),
        "status": "original_capture_only_no_database_change",
        "attempted": len(rows),
        "originals_captured": sum(
            item["result"] == "original_captured" for item in rows
        ),
        "failures": sum(item["result"] != "original_captured" for item in rows),
        "sources": rows,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capture registered original HTML once, without redirects",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = audit_sources(args.output_dir, delay_seconds=0.5)
    print(
        f"Original HTML collected: {report['originals_captured']}"
        f"/{report['attempted']}. No database changes or approvals.",
        flush=True,
    )


if __name__ == "__main__":
    main()
