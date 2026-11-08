"""Encrypted, bounded case conversation for isolated synthetic Preview only.

History is an audit of prior guide turns, NOT an authoritative checkpoint or
source of confirmed facts. Current answers must use freshly loaded case facts,
approved passages, and active rules rather than replaying this history.
"""
from __future__ import annotations

from hashlib import sha256
import json
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.preparation.crypto import decrypt_blob, encrypt_blob
from app.preparation.models import CaseAgentTurn

MAX_TURNS = 20


def load_turns(db: Session, *, case_id: str, owner: str, key: bytes) -> list[dict]:
    rows = db.scalars(
        select(CaseAgentTurn).where(
            CaseAgentTurn.case_id == case_id, CaseAgentTurn.owner_subject == owner,
        ).order_by(CaseAgentTurn.created_at.desc(), CaseAgentTurn.id.desc()).limit(MAX_TURNS)
    ).all()
    results = []
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
            results.append({
                "id": row.id,
                "question": item["question"],
                "answer": item["answer"],
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
    """Persist only user question and server-produced, non-authoritative status."""
    turn_id = str(uuid4())
    content = {
        "question": question,
        "language": language,
        "answer": result["message"],
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
