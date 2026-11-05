"""Deterministic passage extraction for explicitly labeled browser-rendered text.

This is neither server-response HTML nor the entire accessibility tree.
Input must be the page's substantively visible article body, transcribed
without translation, paraphrase, generated requirements or site chrome.
"""
from hashlib import sha256

from app.knowledge.html_extraction import (
    ExtractedHTML, ExtractedPassage, MAX_PASSAGE_CHARS, MAX_PASSAGES,
)

EXTRACTION_VERSION = "browser-text-v1"
MAX_BROWSER_TEXT_BYTES = 65536


def extract_browser_text(raw: bytes) -> ExtractedHTML:
    if not raw or len(raw) > MAX_BROWSER_TEXT_BYTES:
        raise ValueError("Rendered article text is empty or too large")
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Browser-rendered text must be UTF-8") from exc
    if "\x00" in content or "<input " in content or "<script" in content:
        raise ValueError("Capture contains browser controls or unsafe markup")
    paragraphs = [part.strip() for part in content.split("\n\n") if part.strip()]
    if not paragraphs or len(paragraphs) > MAX_PASSAGES:
        raise ValueError("No reviewable article paragraphs")
    parts: list[str] = []
    for para in paragraphs:
        para = " ".join(para.split())
        while len(para) > MAX_PASSAGE_CHARS:
            pos = para.rfind(" ", 1, MAX_PASSAGE_CHARS + 1)
            if pos < 1:
                raise ValueError("Browser article has an unbreakable long token")
            parts.append(para[:pos])
            para = para[pos:].strip()
        if para:
            parts.append(para)
    if not parts or len(parts) > MAX_PASSAGES:
        raise ValueError("Invalid article passage count")
    passages = []
    chunks = []
    offset = 0
    for ordinal, part in enumerate(parts):
        if ordinal:
            chunks.append("\n\n")
            offset += 2
        start = offset
        chunks.append(part)
        offset += len(part)
        passages.append(ExtractedPassage(
            ordinal=ordinal,
            section_path="Browser-rendered official article",
            start_offset=start, end_offset=offset,
            content=part, content_sha256=sha256(part.encode("utf-8")).hexdigest(),
        ))
    return ExtractedHTML("".join(chunks), tuple(passages))
