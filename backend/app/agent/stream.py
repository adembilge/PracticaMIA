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


def _visible_from_complete(visible_lines: list[str], held_follows: bool) -> str:
    if not visible_lines:
        return ""
    if held_follows:
        return "\n".join(visible_lines)
    return "".join(line + "\n" for line in visible_lines)


def split_stream_chunk(buffer: str, incoming: str) -> tuple[str, str]:
    text = buffer + incoming
    if not text:
        return "", ""

    states = _line_states(text)
    visible_lines: list[str] = []
    held_complete: list[str] = []
    incomplete = ""

    for content, is_complete in states:
        if not is_complete:
            incomplete = content
            break
        if _is_marker_line(content):
            held_complete.append(content + "\n")
        else:
            visible_lines.append(content)

    if incomplete:
        held_prefix = "".join(held_complete)
        if _is_marker_line(incomplete):
            visible = _visible_from_complete(visible_lines, held_follows=True)
            return visible, held_prefix + incomplete
        visible = _visible_from_complete(visible_lines, held_follows=False)
        return visible, held_prefix + incomplete

    held = "".join(held_complete)
    held_follows = bool(held_complete)
    visible = _visible_from_complete(visible_lines, held_follows=held_follows)
    return visible, held