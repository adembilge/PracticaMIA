"""Five tools. A passage does not become a rule."""

from checklist import checklist
from procedure import select
from rules import evaluate

_ALLOWED = {
    "search_official_knowledge": {"query", "procedure_id", "jurisdiction", "language"},
    "get_source_evidence": {"source_id", "passage_id"},
    "find_procedure": {"user_context"},
    "evaluate_requirements": {"procedure_id", "user_context"},
    "generate_checklist": {"case_id"},
}
_DROP = {"body", "decision", "password", "review_status", "include_unreviewed", "person_id"}
_NONE = {"outcome": "no evidence", "passages": []}
_EMPTY = {"items": [], "missing": None}


def _none():
    return dict(_NONE)


def _context(payload):
    raw = payload["user_context"]
    if not isinstance(raw, dict):
        raise ValueError("rejected")
    return {key: value for key, value in raw.items() if key not in _DROP}


def _search(payload, search):
    query = payload["query"]
    procedure = payload["procedure_id"]
    jurisdiction = payload["jurisdiction"]
    language = payload["language"]
    if (
        not isinstance(query, str)
        or not query.strip()
        or procedure != "address change"
        or jurisdiction != "Milano"
        or language not in ("English", "Italian")
    ):
        return _none()
    finder = search
    if finder is None:
        from retrieval import search as finder
    return finder(query, procedure, jurisdiction, language)


def _default_evidence(source_id, passage_id):
    from sqlalchemy import text

    from auth import engine

    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT id, source_id, review_status, body
                FROM passage
                WHERE id = :id AND source_id = :source_id
                """
            ),
            {"id": passage_id, "source_id": source_id},
        ).mappings().first()
    if row is None:
        return None
    return dict(row)


def _evidence(payload, evidence):
    source_id = payload["source_id"]
    passage_id = payload["passage_id"]
    lookup = evidence if evidence is not None else _default_evidence
    found = lookup(source_id, passage_id)
    if (
        not isinstance(found, dict)
        or found.get("source_id") != source_id
        or found.get("review_status") != "trusted"
    ):
        return _none()
    return {"passage": found}


def _checklist(payload, cases, caller):
    row = None if cases is None else cases.get(payload["case_id"])
    if not isinstance(caller, str) or not caller or not isinstance(row, dict):
        return dict(_EMPTY)
    if row.get("person_id") != caller:
        return dict(_EMPTY)
    facts = row.get("facts")
    if not isinstance(facts, dict):
        return dict(_EMPTY)
    return checklist(facts)


def invoke(name, payload, caller=None, search=None, evidence=None, cases=None):
    if name not in _ALLOWED or not isinstance(payload, dict) or set(payload) != _ALLOWED[name]:
        raise ValueError("rejected")
    if name == "search_official_knowledge":
        result = _search(payload, search)
    elif name == "get_source_evidence":
        result = _evidence(payload, evidence)
    elif name == "find_procedure":
        result = select(_context(payload))
    elif name == "evaluate_requirements":
        result = evaluate(_context(payload))
    else:
        result = _checklist(payload, cases, caller)
    return {"tool": name, **result}
