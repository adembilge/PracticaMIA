import hashlib

from pydantic import BaseModel


class ChunkDraft(BaseModel):
    heading: str
    content: str
    chunk_index: int
    content_hash: str


def _sections(text: str) -> list[tuple[str, list[str]]]:
    heading = ""
    words: list[str] = []
    sections: list[tuple[str, list[str]]] = []

    for line in text.splitlines():
        if line.startswith("# "):
            if words:
                sections.append((heading, words))
                words = []
            heading = line[2:].strip()
        else:
            words.extend(line.split())

    if words:
        sections.append((heading, words))

    return sections


def _content_hash(content: str) -> str:
    normalized = " ".join(content.split())
    return hashlib.sha256(normalized.encode()).hexdigest()


def chunk_text(
    text: str,
    max_tokens: int = 500,
    overlap_tokens: int = 80,
) -> list[ChunkDraft]:
    if not text:
        return []

    step = max_tokens - overlap_tokens
    chunks: list[ChunkDraft] = []
    chunk_index = 0

    for heading, words in _sections(text):
        start = 0
        while start < len(words):
            window = words[start : start + max_tokens]
            content = " ".join(window)
            chunks.append(
                ChunkDraft(
                    heading=heading,
                    content=content,
                    chunk_index=chunk_index,
                    content_hash=_content_hash(content),
                )
            )
            chunk_index += 1
            if start + max_tokens >= len(words):
                break
            start += step

    return chunks