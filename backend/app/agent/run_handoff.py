"""Project present-day official-channel guidance from an owned saved answer."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.answer_evidence import AnswerEvidenceScopeReader, current_channel_evidence
from app.agent.contract import NextAction, RunHandoff, RunSnapshot
from app.agent.run_requests import read_run_message
from app.auth.tokens import Principal
from app.cases.model import CaseRecord


def read_run_handoff(
    db: Session, snapshot: RunSnapshot, *, principal: Principal, key: bytes,
    read_evidence_scope: AnswerEvidenceScopeReader | None,
) -> RunHandoff | None:
    result = snapshot.result
    if result is None or result.official_channel is None:
        return None
    message = read_run_message(db, thread_id=snapshot.thread_id, run_id=snapshot.run_id, principal=principal, key=key)
    if message is None:
        return None

    language = message.language
    active_case = message.case_id is None or db.scalar(select(CaseRecord.id).where(
        CaseRecord.id == str(message.case_id), CaseRecord.owner_subject == principal.subject,
        CaseRecord.archived_at.is_(None),
    )) is not None
    scope = (
        read_evidence_scope(db, snapshot.thread_id, snapshot.run_id, message.case_id, principal)
        if active_case and read_evidence_scope is not None else None
    )
    evidence_ids = current_channel_evidence(db, result, scope=scope, language=language)
    if not evidence_ids:
        return RunHandoff(
            language=language, status="verification_required",
            next_action=NextAction(
                operation="provide_information",
                label="Verify the current official channel" if language == "en" else "Verifica il canale ufficiale attuale",
            ),
        )

    needs_information = bool(result.missing_information) or result.verification_status in {
        "conflicting_evidence", "unsupported",
    }
    if needs_information:
        action = NextAction(
            operation="provide_information",
            label="Confirm the case details first" if language == "en" else "Conferma prima i dati della pratica",
        )
    else:
        action = NextAction(
            operation="open_official_channel",
            label="Open the official channel" if language == "en" else "Apri il canale ufficiale",
        )
    return RunHandoff(
        language=language, status="verified_channel", official_channel=result.official_channel,
        evidence_ids=evidence_ids, next_action=action,
    )
