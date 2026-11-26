_CITATIONS = "CITATIONS:"
_REFINE = "REFINE:"
_MARKERS = (_CITATIONS, _REFINE)


def _is_marker_line(line: str) -> bool:
    return line.startswith(_CITATIONS) or line.startswith(_REFINE)


def _could_be_marker_prefix(fragment: str) -> bool:
    if _is_marker_line(fragment):
        return False
    return any(marker.startswith(fragment) for marker in _MARKERS)


def split_stream_chunk(buffer: str, incoming: str) -> tuple[str, str]:
    text = buffer + incoming
    if not text:
        return "", ""

    if text.endswith("\n"):
        incomplete = ""
        complete_lines = text.split("\n")
    else:
        parts = text.split("\n")
        incomplete = parts[-1]
        complete_lines = parts[:-1]

    visible_lines: list[str] = []
    held_complete: list[str] = []
    for line in complete_lines:
        if _is_marker_line(line):
            held_complete.append(line)
        else:
            visible_lines.append(line)

    if incomplete:
        if _is_marker_line(incomplete):
            visible = "\n".join(visible_lines)
        else:
            visible = "\n".join(visible_lines)
            if visible_lines:
                visible += "\n"
        held_parts = [*held_complete, incomplete]
        held = held_parts[0] if len(held_parts) == 1 else "\n".join(held_parts)
        return visible, held

    visible = "".join(line + "\n" for line in visible_lines)
    held = "\n".join(held_complete) if held_complete else ""
    return visible, held