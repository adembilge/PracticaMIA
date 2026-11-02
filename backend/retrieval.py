"""Search trusted versions. A passage stays unreviewed."""

from sqlalchemy import text

from auth import engine
from embeddings import embed

PROCEDURE = "address change"
JURISDICTION = "Milano"
LANGUAGES = ("English", "Italian")
NONE = {"outcome": "no evidence", "passages": []}


def _literal(vector):
    return "[" + ",".join(str(value) for value in vector) + "]"


def _none():
    return {"outcome": NONE["outcome"], "passages": []}


def search(query, procedure, jurisdiction, language, limit=5):
    if not isinstance(query, str) or not query.strip():
        return _none()
    if procedure != PROCEDURE or jurisdiction != JURISDICTION or language not in LANGUAGES:
        return _none()
    if not isinstance(limit, int) or limit < 1:
        limit = 5
    # shortcut: combined score only, upgrade when a second ranker is measured
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                WITH matched AS (
                    SELECT
                        p.id,
                        p.source_id,
                        p.review_status,
                        p.body,
                        p.section,
                        p.source_version_id,
                        ts_rank(p.body_tsv, plainto_tsquery('simple', :query))
                            + (1 - (e.vector <=> CAST(:vector AS vector))) AS rank
                    FROM passage AS p
                    JOIN source_version AS v ON v.id = p.source_version_id
                    JOIN embedding AS e ON e.passage_id = p.id
                    WHERE v.review_status = 'trusted'
                      AND p.procedure = :procedure
                      AND p.jurisdiction = :jurisdiction
                      AND p.language = :language
                )
                SELECT
                    id, source_id, review_status, body, section, source_version_id,
                    count(*) OVER () AS total
                FROM matched
                ORDER BY rank DESC, id
                LIMIT :limit
                """
            ),
            {
                "query": query,
                "vector": _literal(embed(query)),
                "procedure": procedure,
                "jurisdiction": jurisdiction,
                "language": language,
                "limit": limit,
            },
        ).mappings().all()
        if not rows:
            return _none()
        citations = {}
        for row in rows:
            found = conn.execute(
                text(
                    """
                    SELECT id, review_status
                    FROM citation
                    WHERE passage_id = :id
                    ORDER BY id
                    """
                ),
                {"id": row["id"]},
            ).mappings().all()
            citations[row["id"]] = [
                {"id": item["id"], "review_status": item["review_status"]} for item in found
            ]
    total = rows[0]["total"]
    if total == 1:
        outcome = "insufficient evidence"
    else:
        outcome = "conflicting evidence"
    return {
        "outcome": outcome,
        "passages": [
            {
                "id": row["id"],
                "source_id": row["source_id"],
                "review_status": row["review_status"],
                "body": row["body"],
                "provenance": {
                    "source_id": row["source_id"],
                    "source_version_id": row["source_version_id"],
                    "section": row["section"],
                },
                "citations": citations[row["id"]],
            }
            for row in rows
        ],
    }
