"""Text already in the file. A missing name stays unreadable."""


def _page(payload, index):
    count = 0
    start = 0
    needle = b"/Type /Page"
    while start < index:
        found = payload.find(needle, start, index)
        if found < 0:
            break
        after = found + len(needle)
        if after >= index or payload[after:after + 1] != b"s":
            count += 1
        start = after
    return count or 1


def _strings(payload):
    found = []
    index = 0
    size = len(payload)
    while index < size:
        if payload[index:index + 1] != b"(":
            index += 1
            continue
        start = index
        index += 1
        raw = bytearray()
        while index < size:
            char = payload[index:index + 1]
            if char == b"\\" and index + 1 < size:
                nxt = payload[index + 1:index + 2]
                if nxt in (b"\\", b"(", b")"):
                    raw.extend(nxt)
                    index += 2
                    continue
            if char == b")":
                index += 1
                break
            raw.extend(char)
            index += 1
        found.append((_page(payload, start), raw.decode("latin-1")))
    return found


def _pages(payload):
    pages = []
    for number, text in _strings(payload):
        if pages and pages[-1]["page"] == number:
            pages[-1]["text"] += "\n" + text
        else:
            pages.append({"page": number, "text": text})
    return pages


def _label(line):
    for label in ("Name:", "Nome:"):
        if line.startswith(label):
            rest = line[len(label):]
            if rest.startswith(" "):
                rest = rest[1:]
            return rest or None
    return None


def _fields(pages):
    name = None
    address = None
    for page in pages:
        for line in page["text"].split("\n"):
            if address is None and "Milano" in line:
                address = line
            if name is None:
                name = _label(line)
    return name, address


def _proposal(proposal):
    if not isinstance(proposal, dict) or set(proposal) != {"name", "address"}:
        return None
    name = proposal["name"]
    address = proposal["address"]
    if not isinstance(name, str) or not name.strip():
        return None
    if not isinstance(address, str) or not address.strip():
        return None
    return name, address


def _image(payload):
    return payload.startswith(b"\x89PNG\r\n\x1a\n") or payload.startswith(b"\xff\xd8\xff")


def _empty():
    return {"status": "unreadable", "pages": [], "name": None, "address": None}


def read(payload, proposal=None):
    if not isinstance(payload, (bytes, bytearray)) or not payload.startswith(b"%PDF"):
        accepted = _proposal(proposal)
        if isinstance(payload, (bytes, bytearray)) and _image(payload) and accepted:
            name, address = accepted
            return {"status": "read", "pages": [], "name": name, "address": address}
        return _empty()
    pages = _pages(payload)
    name, address = _fields(pages)
    if name is None:
        return {"status": "unreadable", "pages": pages, "name": None, "address": None}
    return {"status": "read", "pages": pages, "name": name, "address": address}
