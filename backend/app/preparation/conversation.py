"""Encrypted, bounded case conversation for isolated synthetic Preview only.

History is an audit of prior guide turns, NOT an authoritative checkpoint or
source of confirmed facts. Current answers must use freshly loaded case facts,
approved passages, and active rules rather than replaying this history.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.knowledge.model import KnowledgeSource, KnowledgeSourceVersion
from app.knowledge.quote_verification import CLAIM, ID, verify_exact_quotations
from app.knowledge.search import EvidencePassage, resolve_approved_passage
from app.knowledge.snapshot_model import KnowledgePassage
from app.preparation.crypto import decrypt_blob, encrypt_blob
from app.preparation.models import CaseAgentTurn
from app.rules.engine import JURISDICTION, PROCEDURE

MAX_TURNS = 20


@dataclass(frozen=True)
class SavedCitation:
    source_id: str
    source_version_id: str
    passage_id: str
    source_revision: int

    @classmethod
    def from_passage(cls, passage: EvidencePassage) -> SavedCitation:
        return cls(
            passage.source_id, passage.source_version_id,
            passage.passage_id, passage.source_revision,
        )

    def __post_init__(self) -> None:
        if (
            not isinstance(self.source_id, str) or not 1 <= len(self.source_id) <= 96
            or not isinstance(self.passage_id, str)
            or re.fullmatch(ID, self.passage_id) is None
            or self.passage_id.split(":", 1)[0] != self.source_version_id
            or type(self.source_revision) is not int or self.source_revision < 1
        ):
            raise ValueError("Malformed saved citation")


def _approved(db: Session, passage_id: str) -> EvidencePassage | None:
    return resolve_approved_passage(
        db, citation_id=passage_id, jurisdiction=JURISDICTION,
        procedure_id=PROCEDURE, language="it",
    )


def _verify_for_history(db: Session, result: dict) -> tuple[str | None, list[dict]]:
    quote = result.get("answer")
    if result.get("answer_status") != "answer_generated" or not isinstance(quote, str):
        return None, []
    lines = quote.splitlines()
    if len(quote) > 2000 or not 1 <= len(lines) <= 4:
        return None, []
    matches = [CLAIM.fullmatch(line) for line in lines]
    if any(match is None for match in matches):
        return None, []
    ids = dict.fromkeys(match.group(1) for match in matches if match is not None)
    # Ingestion, approval and withdrawal lock the source row before changing
    # trust. Hold shared locks in a consistent order through the saved turn.
    db.execute(
        select(KnowledgeSource.id)
        .where(KnowledgeSource.id.in_(
            select(KnowledgeSourceVersion.source_id)
            .join(KnowledgePassage, KnowledgePassage.version_id == KnowledgeSourceVersion.id)
            .where(KnowledgePassage.id.in_(ids))
        ))
        .order_by(KnowledgeSource.id)
        .with_for_update(read=True)
    ).all()
    passages = {passage_id: _approved(db, passage_id) for passage_id in ids}
    verified = {key: passage.content for key, passage in passages.items() if passage is not None}
    if not verify_exact_quotations(quote, verified):
        return None, []
    return quote, [
        asdict(SavedCitation.from_passage(passage))
        for passage in passages.values() if passage is not None
    ]


def _history_evidence(
    db: Session, item: dict, checked: dict[str, EvidencePassage | None],
) -> dict:
    if "citations" not in item:
        if item["status"] == "answer_generated":
            return {"answer": item["answer"].partition("\n\n")[0], "citation_status": "unknown"}
        return {"answer": item["answer"]}

    citations = [SavedCitation(**record) for record in item["citations"]]
    quote = item.get("quote")
    if not citations:
        status = {"citation_status": "unavailable"} if item["status"] == "answer_generated" else {}
        return {"answer": item["answer"], **status}
    if not isinstance(quote, str) or len(citations) > 4:
        raise ValueError("Malformed saved quotations")

    views = []
    approved = {}
    for reference in citations:
        passage_id = reference.passage_id
        if passage_id not in checked:
            checked[passage_id] = _approved(db, passage_id)
        passage = checked[passage_id]
        current = passage is not None and SavedCitation.from_passage(passage) == reference
        if current:
            approved[passage_id] = passage.content
        views.append({**asdict(reference), "status": "current" if current else "historical"})
    show_quote = verify_exact_quotations(quote, approved)
    return {
        "answer": item["answer"] + ("\n\n" + quote if show_quote else ""),
        "citations": views,
        "citation_status": "current" if show_quote else "historical",
    }


def load_turns(
    db: Session, *, case_id: str, owner: str, key: bytes, include_evidence: bool = True,
) -> list[dict]:
    rows = db.scalars(
        select(CaseAgentTurn).where(
            CaseAgentTurn.case_id == case_id, CaseAgentTurn.owner_subject == owner,
        ).order_by(CaseAgentTurn.created_at.desc(), CaseAgentTurn.id.desc()).limit(MAX_TURNS)
    ).all()
    results = []
    checked: dict[str, EvidencePassage | None] = {}
    for row in reversed(rows):
        try:
            raw = decrypt_blob(
                row.content_ciphertext, key=key, case_id=case_id,
                owner_subject=owner, document_id=f"agent-turn:{row.id}",
                expected_digest=row.content_sha256,
            )
            item = json.loads(raw)
            if not isinstance(item, dict) or not all(
                isinstance(item.get(field), str)
                for field in ("question", "answer", "action", "status", "language")
            ):
                raise ValueError("Malformed history")
            if not include_evidence:
                results.append({"question": item["question"], "action": item["action"]})
                continue
            results.append({
                "id": row.id,
                "question": item["question"],
                **_history_evidence(db, item, checked),
                "action": item["action"],
                "status": item["status"],
                "language": item["language"],
                "next_action": item.get("next_action"),
                "created_at": row.created_at.isoformat(),
            })
        except Exception:
            raise HTTPException(503, "Saved conversation is unavailable") from None
    return results


def save_turn(db: Session, *, case_id: str, owner: str, key: bytes,
              question: str, language: str, result: dict) -> None:
    """Persist the server-produced turn and its exact verified evidence."""
    turn_id = str(uuid4())
    quote, citations = _verify_for_history(db, result)
    content = {
        "question": question,
        "language": language,
        "answer": result["message"],
        "quote": quote,
        "citations": citations,
        "action": result["action"],
        "status": result["status"],
        "next_action": result.get("next_action"),
    }
    raw = json.dumps(content, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":")).encode("utf-8")
    db.add(CaseAgentTurn(
        id=turn_id, case_id=case_id, owner_subject=owner,
        content_sha256=sha256(raw).hexdigest(),
        content_ciphertext=encrypt_blob(
            raw, key=key, case_id=case_id, owner_subject=owner,
            document_id=f"agent-turn:{turn_id}",
        ),
    ))
    db.flush()
    # Retain at most the most recent MAX_TURNS. Physical deletion means old
    # history is not copied into a permanent shared retrieval index.
    old = db.scalars(
        select(CaseAgentTurn).where(
            CaseAgentTurn.case_id == case_id, CaseAgentTurn.owner_subject == owner,
        ).order_by(CaseAgentTurn.created_at.desc(), CaseAgentTurn.id.desc())
         .offset(MAX_TURNS)
    ).all()
    for item in old:
        db.delete(item)
    db.commit()
