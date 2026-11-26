_CITATIONS = "CITATIONS:"
_REFINE = "REFINE:"


def _is_marker_line(line: str) -> bool:
    return line.startswith(_CITATIONS) or line.startswith(_REFINE)


def _could_be_marker_prefix(fragment: str) -> bool:
    if _is_marker_line(fragment):
        return False
    return _CITATIONS.startswith(fragment) or _REFINE.startswith(fragment)


def _line_states(text: str) -> list[tuple[str, bool]]:
    states: list[tuple[str, bool]] = []
    start = 0
    for i, ch in enumerate(text):
        if ch == "\n":
            states.append((text[start:i], True))
            start = i + 1
    if start < len(text):
        states.append((text[start:], False))
    return states


def _visible_line_suffix(items: list[tuple[str, str]], visible_index: int) -> str:
    rest = items[visible_index + 1 :]
    if not rest:
        return "\n"
    if any(kind == "visible" for kind, _ in rest):
        return "\n"
    if rest[-1][0] == "incomplete":
        if _is_marker_line(rest[-1][1]):
            return ""
        return "\n"
    # trailing held complete lines only
    return ""


def split_stream_chunk(buffer: str, incoming: str) -> tuple[str, str]:
    text = buffer + incoming
    if not text:
        return "", ""

    states = _line_states(text)
    items: list[tuple[str, str]] = []
    for content, is_complete in states:
        if not is_complete:
            items.append(("incomplete", content))
            break
        if _is_marker_line(content):
            items.append(("held", content + "\n"))
        else:
            items.append(("visible", content))

    visible_parts: list[str] = []
    held_parts: list[str] = []
    for i, (kind, value) in enumerate(items):
        if kind == "visible":
            visible_parts.append(value + _visible_line_suffix(items, i))
        elif kind == "held":
            held_parts.append(value)

    visible = "".join(visible_parts)
    incomplete = ""
    for kind, value in reversed(items):
        if kind == "incomplete":
            incomplete = value
            break
    held = "".join(held_parts) + incomplete
    return visible, held