import pytest

from ingest.catalog import load_sources
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