from app.agent.stream import split_stream_chunk


def test_holds_citation_line():
    visible, held = split_stream_chunk("", "Hello\nCITATIONS: abc")
    assert visible == "Hello"
    assert held == "CITATIONS: abc"


def test_holds_partial_marker():
    visible, held = split_stream_chunk("", "Hello\nCITAT")
    assert visible == "Hello\n"
    assert held == "CITAT"
    visible, held = split_stream_chunk(held, "IONS: abc")
    assert visible == ""
    assert held == "CITATIONS: abc"


def test_holds_refine_line():
    visible, held = split_stream_chunk("", "Done\nREFINE: permesso")
    assert visible == "Done"
    assert "REFINE" not in visible