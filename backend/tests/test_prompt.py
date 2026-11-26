from app.agent.prompt import build_prompt


def test_prompt_locks_language_and_chunk_id():
    state = {
        "question": "How do I renew?",
        "language": "en",
        "history": [{"role": "user", "content": "earlier"}],
        "chunks": [{"id": "chunk-1", "title": "Permesso", "fetched_at": "2026-11-01", "heading": "Rinnovo", "content": "testo"}],
    }
    messages = build_prompt(state)
    assert messages[0]["role"] == "system"
    assert "Write in English." in messages[0]["content"]
    assert "Do not write a URL." in messages[0]["content"]
    assert "id: chunk-1" in messages[1]["content"]
    assert "earlier" in messages[1]["content"]