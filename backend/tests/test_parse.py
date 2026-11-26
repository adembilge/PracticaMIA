from app.agent.parse import parse_generation, strip_urls, validate_citations


def test_parse_citations_and_refine():
    raw = "Renew at the Questura.\nCITATIONS: aaa, bbb\nREFINE: rinnovo permesso"
    answer, ids, refine = parse_generation(raw)
    assert answer == "Renew at the Questura."
    assert ids == ["aaa", "bbb"]
    assert refine == "rinnovo permesso"


def test_parse_without_refine():
    answer, ids, refine = parse_generation("Testo.\nCITATIONS: aaa")
    assert refine is None
    assert ids == ["aaa"]


def test_parse_without_marker():
    answer, ids, refine = parse_generation("Solo testo.")
    assert answer == "Solo testo."
    assert ids == []
    assert refine is None


def test_empty_refine_is_none():
    _answer, _ids, refine = parse_generation("Testo.\nCITATIONS:\nREFINE:   ")
    assert refine is None


def test_validate_drops_unknown_ids():
    chunks = [
        {
            "id": "aaa",
            "title": "T",
            "url": "https://www.poliziadistato.it/articolo/225",
            "heading": "H",
            "fetched_at": "2026-11-01",
        }
    ]
    cites = validate_citations(["aaa", "fake"], chunks)
    assert [item["chunk_id"] for item in cites] == ["aaa"]
    assert cites[0]["url"].endswith("/225")


def test_strip_urls():
    assert "evil.example" not in strip_urls("See https://evil.example/a please.")
    assert strip_urls("See https://evil.example/a please.") == "See  please."