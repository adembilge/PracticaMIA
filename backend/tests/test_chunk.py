import hashlib

from ingest.chunk import ChunkDraft, chunk_text


def _sample_text() -> str:
    before = " ".join(["word"] * 600)
    after = " ".join(["word"] * 600)
    return f"{before}\n# Residenza\n{after}"


def test_chunk_empty_text():
    assert chunk_text("") == []


def test_chunk_word_windows_and_heading():
    chunks = chunk_text(_sample_text())
    assert len(chunks) >= 3

    for index in range(len(chunks) - 1):
        left = chunks[index]
        right = chunks[index + 1]
        if left.heading != right.heading:
            continue
        left_words = left.content.split()
        if len(left_words) < 80:
            continue
        assert left_words[-80:] == right.content.split()[:80]

    residenza_started = False
    for chunk in chunks:
        if chunk.heading == "Residenza":
            residenza_started = True
            assert chunk.heading == "Residenza"
            break
        assert chunk.heading == ""
    assert residenza_started

    first_residenza = next(c for c in chunks if c.heading == "Residenza")
    assert first_residenza.heading == "Residenza"


def test_chunk_content_hash():
    text = " ".join(["word"] * 120)
    chunks = chunk_text(text, max_tokens=50, overlap_tokens=10)
    assert chunks
    for chunk in chunks:
        normalized = " ".join(chunk.content.split())
        expected = hashlib.sha256(normalized.encode()).hexdigest()
        assert chunk.content_hash == expected


def test_chunk_index_increments_across_sections():
    chunks = chunk_text(_sample_text())
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))