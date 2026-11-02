"""Requirement rows cite passages. A write cannot promote the row."""
import hashlib

from fastapi import APIRouter, Request
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException

from auth import _body, _caller, engine

router = APIRouter()
FILES = frozenset(
    {
        "docs/research/DOCUMENTS.md",
        "docs/research/DEADLINES.md",
        "docs/research/SUBMISSION.md",
        "docs/research/RELATED.md",
    }
)


def citation_id(requirement_id, passage_id):
    raw = "%s\n%s" % (requirement_id, passage_id)
    return hashlib.sha256(raw.encode()).hexdigest()


def _checked(body):
    if set(body) != {"id", "file", "passages"}:
        return None
    requirement_id = body["id"]
    file = body["file"]
    passages = body["passages"]
    if not isinstance(requirement_id, str) or not requirement_id:
        return None
    if file not in FILES:
        return None
    if not isinstance(passages, list) or not passages:
        return None
    rows = []
    seen = set()
    for passage_id in passages:
        if not isinstance(passage_id, str) or not passage_id or passage_id in seen:
            return None
        seen.add(passage_id)
        rows.append(
            {
                "id": citation_id(requirement_id, passage_id),
                "passage_id": passage_id,
            }
        )
    return requirement_id, file, rows


def _public(requirement_id, file, review_status, citations):
    return {
        "id": requirement_id,
        "file": file,
        "review_status": review_status,
        "citations": [
            {
                "id": row["id"],
                "passage_id": row["passage_id"],
                "source_id": row["source_id"],
                "source_version_id": row["source_version_id"],
                "section": row["section"],
                "review_status": row["review_status"],
            }
            for row in citations
        ],
    }


def _load(conn, requirement_id):
    requirement = conn.execute(
        text(
            """
            SELECT id, file, review_status
            FROM requirement_row
            WHERE id = :id
            """
        ),
        {"id": requirement_id},
    ).mappings().first()
    if requirement is None:
        return None
    citations = conn.execute(
        text(
            """
            SELECT c.id, c.passage_id, c.review_status,
                   p.source_id, p.source_version_id, p.section
            FROM citation AS c
            JOIN passage AS p ON p.id = c.passage_id
            WHERE c.requirement_row_id = :id
            ORDER BY c.id
            """
        ),
        {"id": requirement_id},
    ).mappings().all()
    return _public(
        requirement["id"],
        requirement["file"],
        requirement["review_status"],
        citations,
    )


@router.post("/v1/requirement")
async def load_requirement(request: Request):
    _caller(request)
    checked = _checked(await _body(request))
    if checked is None:
        raise HTTPException(status_code=400)
    requirement_id, file, rows = checked
    try:
        with engine.begin() as conn:
            for row in rows:
                passage = conn.execute(
                    text(
                        """
                        SELECT p.source_id, p.source_version_id, p.section, v.review_status
                        FROM passage AS p
                        JOIN source_version AS v ON v.id = p.source_version_id
                        WHERE p.id = :id
                        """
                    ),
                    {"id": row["passage_id"]},
                ).mappings().first()
                if passage is None or passage["review_status"] != "trusted":
                    raise HTTPException(status_code=400)
                row["source_id"] = passage["source_id"]
                row["source_version_id"] = passage["source_version_id"]
                row["section"] = passage["section"]
                row["review_status"] = "unreviewed"
            existing = conn.execute(
                text(
                    """
                    SELECT file, review_status
                    FROM requirement_row
                    WHERE id = :id
                    """
                ),
                {"id": requirement_id},
            ).mappings().first()
            if existing is not None:
                stored = conn.execute(
                    text(
                        """
                        SELECT id, passage_id
                        FROM citation
                        WHERE requirement_row_id = :id
                        """
                    ),
                    {"id": requirement_id},
                ).mappings().all()
                same = {(row["id"], row["passage_id"]) for row in stored}
                incoming = {(row["id"], row["passage_id"]) for row in rows}
                if (
                    existing["file"] != file
                    or existing["review_status"] != "unreviewed"
                    or same != incoming
                ):
                    raise HTTPException(status_code=400)
            else:
                conn.execute(
                    text(
                        """
                        INSERT INTO requirement_row (id, file, review_status)
                        VALUES (:id, :file, 'unreviewed')
                        """
                    ),
                    {"id": requirement_id, "file": file},
                )
                for row in rows:
                    conn.execute(
                        text(
                            """
                            INSERT INTO citation (
                                id, requirement_row_id, passage_id, review_status
                            ) VALUES (
                                :id, :requirement_id, :passage_id, 'unreviewed'
                            )
                            """
                        ),
                        {
                            "id": row["id"],
                            "requirement_id": requirement_id,
                            "passage_id": row["passage_id"],
                        },
                    )
    except IntegrityError:
        raise HTTPException(status_code=400)
    return _public(requirement_id, file, "unreviewed", rows)


@router.get("/v1/requirement/{requirement_id}")
def read_requirement(requirement_id: str, request: Request):
    _caller(request)
    with engine.begin() as conn:
        body = _load(conn, requirement_id)
    if body is None:
        raise HTTPException(status_code=404)
    return body
