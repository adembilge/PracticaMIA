import re

from app.agent.state import Citation


def strip_urls(text: str) -> str:
    return re.sub(r"https?://\S+", "", text)


def _parse_ids(value: str) -> list[str]:
    return [part for part in (piece.strip() for piece in value.split(",")) if part]


def parse_generation(raw: str) -> tuple[str, list[str], str | None]:
    lines = raw.splitlines()
    citation_ids: list[str] = []
    refine: str | None = None
    answer_end = len(lines)

    for index, line in enumerate(lines):
        if line.startswith("CITATIONS:"):
            answer_end = min(answer_end, index)
            citation_ids = _parse_ids(line[len("CITATIONS:") :])
        elif line.startswith("REFINE:"):
            answer_end = min(answer_end, index)
            value = line[len("REFINE:") :].strip()
            refine = value or None

    answer = strip_urls("\n".join(lines[:answer_end]).strip())
    return answer, citation_ids, refine


def validate_citations(ids: list[str], chunks: list[dict]) -> list[Citation]:
    by_id = {chunk["id"]: chunk for chunk in chunks}
    cites: list[Citation] = []
    for chunk_id in ids:
        chunk = by_id.get(chunk_id)
        if chunk is None:
            continue
        cites.append(
            Citation(
                chunk_id=chunk_id,
                title=chunk["title"],
                url=chunk["url"],
                heading=chunk["heading"],
                fetched_at=chunk["fetched_at"],
            )
        )
    return cites