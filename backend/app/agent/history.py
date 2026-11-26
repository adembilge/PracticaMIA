MAX_HISTORY_MESSAGES = 6
MAX_CONTENT_CHARS = 500


def trim_history(messages: list[dict]) -> list[dict]:
    kept = messages[-MAX_HISTORY_MESSAGES:]
    out: list[dict] = []
    for msg in kept:
        new_msg = dict(msg)
        content = new_msg.get("content")
        if isinstance(content, str) and len(content) > MAX_CONTENT_CHARS:
            new_msg["content"] = content[:MAX_CONTENT_CHARS]
        out.append(new_msg)
    return out