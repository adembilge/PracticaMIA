from html.parser import HTMLParser
from urllib.parse import urljoin

from ingest.fetch import host_allowed
from ingest.models import SourceSpec


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_anchor = False
        self._href = ""
        self._text_parts: list[str] = []
        self.anchors: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        self._in_anchor = True
        self._text_parts = []
        self._href = ""
        for name, value in attrs:
            if name == "href":
                self._href = value or ""
                break

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or not self._in_anchor:
            return
        self.anchors.append((self._href, "".join(self._text_parts)))
        self._in_anchor = False

    def handle_data(self, data: str) -> None:
        if self._in_anchor:
            self._text_parts.append(data)


def _keyword_match(absolute_url: str, link_text: str, keywords: list[str]) -> bool:
    url_folded = absolute_url.casefold()
    text_folded = link_text.casefold()
    for keyword in keywords:
        folded = keyword.casefold()
        if folded in url_folded or folded in text_folded:
            return True
    return False


def discover(html: str, page_url: str, source: SourceSpec, seen: set[str]) -> list[str]:
    if len(seen) >= source.max_pages:
        return []

    parser = _AnchorParser()
    parser.feed(html)

    found: list[str] = []
    included: set[str] = set()

    for href, text in parser.anchors:
        absolute = urljoin(page_url, href)
        if absolute in seen or absolute in included:
            continue
        if not host_allowed(absolute):
            continue
        if not _keyword_match(absolute, text, source.keywords):
            continue
        found.append(absolute)
        included.add(absolute)

    return found