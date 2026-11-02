"""Local ingest. A passage stays unreviewed."""
import hashlib
import re
from html.parser import HTMLParser
from pathlib import Path

from fastapi import APIRouter, Request
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException

from auth import _body, _caller, engine
from embeddings import embed

router = APIRouter()
MODEL = "local"
EMBEDDING_VERSION = "1"
FIELDS = {"id", "source_id", "source_version_id", "section", "body"}
# shortcut: uncompressed PDF literal strings only, upgrade when a real PDF is required.
_PDF_STRING = re.compile(br"\((?:\\.|[^\\)])*\)")
_HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


def collect(path):
    text_path = str(path)
    lowered = text_path.lower()
    if lowered.startswith("http://") or lowered.startswith("https://"):
        return None
    file = Path(path)
    if not file.is_file():
        return None
    data = file.read_bytes()
    if not data:
        return None
    return data


def _collapse(value):
    return " ".join(value.split())


class _Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.section = None
        self.body = []
        self.heading = None
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.skip += 1
        elif tag in _HEADINGS and self.skip == 0:
            self._flush()
            self.heading = []

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.skip:
            self.skip -= 1
        elif tag in _HEADINGS and self.heading is not None:
            self.section = _collapse("".join(self.heading)) or None
            self.heading = None
        elif tag in {"p", "li", "td", "th", "div", "tr"} and self.skip == 0 and self.heading is None:
            self.body.append(" ")

    def handle_data(self, data):
        if self.skip:
            return
        if self.heading is not None:
            self.heading.append(data)
        else:
            self.body.append(data)

    def close(self):
        super().close()
        self._flush()

    def _flush(self):
        body = _collapse("".join(self.body))
        if body:
            self.parts.append((self.section, body))
        self.body = []


def _pdf_parts(data):
    found = []
    for match in _PDF_STRING.finditer(data):
        raw = match.group()[1:-1]
        raw = (
            raw.replace(br"\(", b"(")
            .replace(br"\)", b")")
            .replace(br"\\", b"\\")
        )
        word = _collapse(raw.decode("latin-1", errors="ignore"))
        if word:
            found.append(word)
    if not found:
        return []
    return [(None, " ".join(found))]


def extract(path, data):
    name = str(path).lower()
    if name.endswith(".pdf") or data.startswith(b"%PDF"):
        return _pdf_parts(data)
    page = _Page()
    page.feed(data.decode("utf-8", errors="replace"))
    page.close()
    return page.parts


def passage_id(version_id, section, body):
    raw = "%s\n%s\n%s" % (version_id, "" if section is None else section, body)
    return hashlib.sha256(raw.encode()).hexdigest()


def chunk(document_id, version_id, parts):
    rows = []
    for section, body in parts:
        if not body:
            continue
        rows.append(
            {
                "id": passage_id(version_id, section, body),
                "source_id": document_id,
                "source_version_id": version_id,
                "section": section,
                "body": body,
            }
        )
    return rows


def prepare(path, document_id, version_id):
    data = collect(path)
    if data is None:
        return None
    passages = chunk(document_id, version_id, extract(path, data))
    if not passages:
        return None
    return passages


def run(path, document_id, version_id, post):
    passages = prepare(path, document_id, version_id)
    if passages is None:
        return 1
    status = post(document_id, version_id, passages)
    if hasattr(status, "status_code"):
        status = status.status_code
    return 0 if status == 200 else 1


def _checked(body, document_id, version_id):
    if set(body) != {"passages"} or not isinstance(body["passages"], list) or not body["passages"]:
        return None
    rows = []
    seen = set()
    for item in body["passages"]:
        if not isinstance(item, dict) or set(item) != FIELDS:
            return None
        section = item["section"]
        text_body = item["body"]
        if section is not None and not isinstance(section, str):
            return None
        if not isinstance(text_body, str) or not text_body:
            return None
        if item["source_id"] != document_id or item["source_version_id"] != version_id:
            return None
        expected = passage_id(version_id, section, text_body)
        if item["id"] != expected or expected in seen:
            return None
        seen.add(expected)
        rows.append({"id": expected, "section": section, "body": text_body})
    return rows


def _same(stored, incoming):
    left = {(row["id"], row["section"], row["body"]) for row in stored}
    right = {(row["id"], row["section"], row["body"]) for row in incoming}
    return left == right


def _literal(vector):
    return "[" + ",".join(str(value) for value in vector) + "]"


def _public(rows):
    return {
        "passages": [
            {
                "id": row["id"],
                "section": row["section"],
                "body": row["body"],
                "review_status": "unreviewed",
            }
            for row in rows
        ]
    }


@router.post("/v1/source/{document_id}/version/{version_id}/passages")
async def write_passages(document_id: str, version_id: str, request: Request):
    _caller(request)
    rows = _checked(await _body(request), document_id, version_id)
    if rows is None:
        raise HTTPException(status_code=400)
    try:
        with engine.begin() as conn:
            status = conn.execute(
                text(
                    """
                    SELECT review_status FROM source_version
                    WHERE id = :version_id AND source_document_id = :document_id
                    """
                ),
                {"version_id": version_id, "document_id": document_id},
            ).scalar()
            if status is None:
                raise HTTPException(status_code=404)
            if status != "trusted":
                raise HTTPException(status_code=400)
            stored = conn.execute(
                text(
                    """
                    SELECT id, section, body FROM passage
                    WHERE source_version_id = :version_id
                    """
                ),
                {"version_id": version_id},
            ).mappings().all()
            if stored:
                if not _same(stored, rows):
                    raise HTTPException(status_code=400)
            else:
                for row in rows:
                    conn.execute(
                        text(
                            """
                            INSERT INTO passage (
                                id, source_version_id, source_id, section, body, review_status
                            ) VALUES (
                                :id, :version_id, :source_id, :section, :body, 'unreviewed'
                            )
                            """
                        ),
                        {
                            "id": row["id"],
                            "version_id": version_id,
                            "source_id": document_id,
                            "section": row["section"],
                            "body": row["body"],
                        },
                    )
                    conn.execute(
                        text(
                            """
                            INSERT INTO embedding (
                                passage_id, model_name, embedding_version, vector
                            ) VALUES (
                                :id, :model, :embedding_version, CAST(:vector AS vector)
                            )
                            """
                        ),
                        {
                            "id": row["id"],
                            "model": MODEL,
                            "embedding_version": EMBEDDING_VERSION,
                            "vector": _literal(embed(row["body"])),
                        },
                    )
    except IntegrityError:
        raise HTTPException(status_code=400)
    return _public(rows)
