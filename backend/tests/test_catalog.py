from pathlib import Path

import pytest

from ingest.catalog import load_sources
from ingest.discover import discover
from ingest.models import SourceSpec

SAMPLE_YAML = """\
sources:
  - id: one
    topic: immigrazione
    name: One
    batch: a
    portal_url: https://www.poliziadistato.it/articolo/225
    urls: ["https://www.poliziadistato.it/articolo/225"]
    keywords: [permesso]
  - id: two
    topic: anagrafe
    name: Two
    batch: a
    portal_url: https://www.anagrafenazionale.interno.it/area-cittadino/
    urls: ["https://www.anagrafenazionale.interno.it/area-cittadino/"]
    keywords: [residenza]
  - id: three
    topic: fisco
    name: Three
    batch: b
    portal_url: https://www.agenziaentrate.gov.it/
    urls: ["https://www.agenziaentrate.gov.it/"]
    keywords: [IMU]
"""


@pytest.fixture
def catalog_path(tmp_path):
    path = tmp_path / "sources.yaml"
    path.write_text(SAMPLE_YAML, encoding="utf-8")
    return path


def test_load_sources_batch_a_returns_two(catalog_path):
    sources = load_sources("a", catalog_path)
    assert len(sources) == 2
    assert all(isinstance(s, SourceSpec) for s in sources)
    assert {s.id for s in sources} == {"one", "two"}


def test_unknown_topic_raises_value_error():
    with pytest.raises(ValueError):
        SourceSpec(
            id="x",
            topic="spor",
            name="X",
            batch="a",
            portal_url="https://example.com",
            urls=["https://example.com"],
            keywords=[],
        )


def test_http_portal_url_raises_value_error():
    with pytest.raises(ValueError):
        SourceSpec(
            id="x",
            topic="immigrazione",
            name="X",
            batch="a",
            portal_url="http://example.com",
            urls=["https://example.com"],
            keywords=[],
        )


def test_load_sources_batch_a_official_catalog_returns_fourteen():
    sources = load_sources("a")
    assert len(sources) == 14
    normattiva = [s for s in sources if s.id.startswith("normattiva-")]
    assert len(normattiva) == 5
    assert all(s.portal_url == "https://www.normattiva.it/" for s in normattiva)


def test_catalog_excludes_stale_brochure():
    path = Path(__file__).resolve().parents[1] / "ingest" / "sources.yaml"
    text = path.read_text(encoding="utf-8")
    assert "0554_initaliainregola" not in text


def _discover_source() -> SourceSpec:
    return SourceSpec(
        id="polizia-permesso",
        topic="immigrazione",
        name="polizia permesso",
        batch="a",
        portal_url="https://www.poliziadistato.it/articolo/225",
        urls=["https://www.poliziadistato.it/articolo/225"],
        keywords=["permesso", "soggiorno", "questura", "rinnovo"],
        max_pages=30,
    )


def test_discover_returns_only_allowed_keyword_link():
    source = _discover_source()
    page_url = "https://www.poliziadistato.it/articolo/225"
    html = """
    <a href="/foo/permesso">Rinnovo</a>
    <a href="https://evil.example/permesso">permesso</a>
    """
    seen: set[str] = set()
    found = discover(html, page_url, source, seen)
    assert found == ["https://www.poliziadistato.it/foo/permesso"]


def test_discover_omits_urls_already_in_seen():
    source = _discover_source()
    page_url = "https://www.poliziadistato.it/articolo/225"
    url = "https://www.poliziadistato.it/foo/permesso"
    html = f'<a href="/foo/permesso">Rinnovo</a>'
    seen = {url}
    found = discover(html, page_url, source, seen)
    assert found == []


def test_discover_returns_empty_when_seen_reaches_max_pages():
    source = _discover_source()
    page_url = "https://www.poliziadistato.it/articolo/225"
    html = '<a href="/foo/permesso">permesso</a>'
    seen = {f"https://www.poliziadistato.it/p{i}" for i in range(30)}
    found = discover(html, page_url, source, seen)
    assert found == []
    assert len(seen) == 30


def test_discover_deduplicates_within_result():
    source = _discover_source()
    page_url = "https://www.poliziadistato.it/articolo/225"
    html = """
    <a href="/foo/permesso">one</a>
    <a href="/foo/permesso">two</a>
    """
    found = discover(html, page_url, source, set())
    assert found == ["https://www.poliziadistato.it/foo/permesso"]


def test_discover_keyword_match_is_case_insensitive():
    source = _discover_source()
    page_url = "https://www.poliziadistato.it/articolo/225"
    html = '<a href="https://www.poliziadistato.it/page">PERMESSO</a>'
    found = discover(html, page_url, source, set())
    assert found == ["https://www.poliziadistato.it/page"]