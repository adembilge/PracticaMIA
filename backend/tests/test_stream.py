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


def test_completed_visible_lines_keep_single_trailing_newline():
    visible, held = split_stream_chunk("", "Hello\n")
    assert visible == "Hello\n"
    assert held == ""

    visible, held = split_stream_chunk("", "A\nB\n")
    assert visible == "A\nB\n"
    assert held == ""


def test_completed_marker_line_held_with_terminator():
    visible, held = split_stream_chunk("", "CITATIONS: abc\n")
    assert visible == ""
    assert held == "CITATIONS: abc\n"


def test_visible_before_completed_marker_without_extra_blank():
    visible, held = split_stream_chunk("", "Hello\nCITATIONS: abc\n")
    assert visible == "Hello"
    assert held == "CITATIONS: abc\n"


def test_blank_line_before_held_marker_preserved():
    visible, held = split_stream_chunk("", "Hello\n\nCITATIONS: abc")
    assert visible == "Hello\n"
    assert held == "CITATIONS: abc"

    visible, held = split_stream_chunk("", "Hello\n\n")
    assert visible == "Hello\n\n"
    assert held == ""


def test_visible_lines_after_held_marker_keep_trailing_newline():
    visible, held = split_stream_chunk("", "CITATIONS: abc\nHello\n")
    assert visible == "Hello\n"
    assert held == "CITATIONS: abc\n"

    visible, held = split_stream_chunk("", "Hello\nCITATIONS: abc\nWorld\n")
    assert visible == "Hello\nWorld\n"
    assert held == "CITATIONS: abc\n"