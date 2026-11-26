from copy import deepcopy

from app.agent.history import trim_history


def _msg(i: int, content: str = "x") -> dict:
    return {"role": "user" if i % 2 == 0 else "assistant", "id": f"msg-{i}", "content": content}


def test_trim_history_keeps_last_six_and_caps_content():
    long_content = "a" * 600
    messages = [_msg(i, f"c{i}") for i in range(8)]
    messages[6] = _msg(6, long_content)
    snapshot = deepcopy(messages)
    ids_before = [id(m) for m in messages]

    result = trim_history(messages)

    assert len(result) == 6
    assert [m["id"] for m in result] == [f"msg-{i}" for i in range(2, 8)]
    assert result[4]["content"] == "a" * 500
    assert result[0]["content"] == "c2"
    assert result[-1]["content"] == "c7"
    for i, kept in enumerate(result):
        src_id = 2 + i
        assert kept["role"] == snapshot[src_id]["role"]
        assert kept["id"] == snapshot[src_id]["id"]
    assert messages == snapshot
    assert [id(m) for m in messages] == ids_before
    assert all(result[i] is not messages[2 + i] for i in range(6))