"""Conservative, deterministic HTML text extraction (unreviewed material only).

Avoids script, navigation and form text. Not a substitute for human review:
complex tables, page layout and site-specific JavaScript may not preserve
legal meaning. Every passage references exact offsets in normalized_text.
"""
from dataclasses import dataclass
from html.parser import HTMLParser
from hashlib import sha256
import re

EXTRACTION_VERSION = "html-v1"
MAX_HTML_BYTES = 524288
MAX_PASSAGES = 300
MAX_PASSAGE_CHARS = 1200
IGNORED = frozenset({"script", "style", "noscript", "svg", "nav",
                     "footer", "header", "form", "aside", "template"})
BLOCKS = frozenset({"p", "li", "div", "section", "article", "tr",
                    "blockquote", "h1", "h2", "h3", "h4", "h5", "h6"})
HEADINGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})


@dataclass(frozen=True)
class ExtractedPassage:
    ordinal: int
    section_path: str
    start_offset: int
    end_offset: int
    content: str
    content_sha256: str


@dataclass(frozen=True)
class ExtractedHTML:
    normalized_text: str
    passages: tuple[ExtractedPassage, ...]


class _DocumentParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self._heading = "Document"
        self._heading_tag = None
        self._buffer = []
        self._paragraphs = []

    def _flush(self):
        content = " ".join("".join(self._buffer).split())
        self._buffer.clear()
        if not content:
            return
        if self._heading_tag:
            self._heading = content[:300]
        else:
            self._paragraphs.append((self._heading, content))

    def handle_starttag(self, tag, attrs):
        if self._ignored_depth:
            self._ignored_depth += 1
            return
        if tag in IGNORED:
            self._flush()
            self._ignored_depth = 1
            return
        if tag in BLOCKS:
            self._flush()
        if tag in HEADINGS:
            self._heading_tag = tag
        if tag == "br":
            self._buffer.append(" ")

    def handle_endtag(self, tag):
        if self._ignored_depth:
            self._ignored_depth -= 1
            return
        if tag in BLOCKS:
            self._flush()
        if tag in HEADINGS:
            self._heading_tag = None

    def handle_startendtag(self, tag, attrs):
        if tag == "br" and not self._ignored_depth:
            self._buffer.append(" ")

    def handle_data(self, data):
        if not self._ignored_depth:
            self._buffer.append(data)

    def result(self):
        self._flush()
        return self._paragraphs


def _split_text(value: str):
    """Split at whitespace boundaries; never silently drop source words."""
    remaining = value
    while len(remaining) > MAX_PASSAGE_CHARS:
        cut = remaining.rfind(" ", 1, MAX_PASSAGE_CHARS + 1)
        if cut < 1:
            cut = MAX_PASSAGE_CHARS
        yield remaining[:cut]
        remaining = remaining[cut:].lstrip()
    if remaining:
        yield remaining


def extract_html(raw: bytes) -> ExtractedHTML:
    if not raw or len(raw) > MAX_HTML_BYTES:
        raise ValueError("HTML snapshot is empty or exceeds size limit")
    # UTF-8 decoding is deliberate; silent replacement could corrupt citations.
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("HTML must be UTF-8; other encodings require review") from exc

    parser = _DocumentParser()
    parser.feed(content)
    paragraphs = parser.result()
    if not paragraphs:
        raise ValueError("No reviewable HTML text was extracted")

    pieces = []
    for heading, paragraph in paragraphs:
        if not paragraph.strip():
            continue
        for part in _split_text(paragraph):
            if part:
                pieces.append((heading, part))
    if not pieces or len(pieces) > MAX_PASSAGES:
        raise ValueError("Extracted passage count outside allowed range")

    text_parts = []
    passages = []
    offset = 0
    for index, (heading, part) in enumerate(pieces):
        if index:
            text_parts.append("\n\n")
            offset += 2
        start = offset
        text_parts.append(part)
        offset += len(part)
        passages.append(ExtractedPassage(
            ordinal=index, section_path=heading[:300],
            start_offset=start, end_offset=offset,
            content=part,
            content_sha256=sha256(part.encode("utf-8")).hexdigest(),
        ))
    normalized_text = "".join(text_parts)
    if len(normalized_text) > 250000:
        raise ValueError("Extracted text too large")
    assert all(normalized_text[p.start_offset:p.end_offset] == p.content
               for p in passages)
    return ExtractedHTML(normalized_text, tuple(passages))
