"""Resolve an owned saved-case reference without changing a run's case binding."""

import re
from uuid import UUID, uuid4

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.agent.case_context import read_worker_case_context
from app.agent.contract import AnswerResult, ClarifyingQuestion, ContractModel, SavedCaseChoice
from app.agent.filing_clarification import (
    MARRIAGE_BANNS, SAVED_CASE_FILING, confirm_saved_intake, marriage_municipality_question,
)
from app.agent.run_requests import ACTIVE_STATUSES, AgentRunRequest, StoredMessage
from app.agent.threads import AgentThread, active_case_links
from app.auth.tokens import Principal
from app.cases.model import CaseRecord
from app.knowledge.entity_matching import normalize_name
from app.rules.engine import JURISDICTION, PROCEDURE


OTHER_CASE_CUE = re.compile(
    r"\b(?:other (?:case|application)|altra (?:pratica|domanda)|altro caso)\b"
)


def _label(case: CaseRecord, language: str) -> str:
    title = "Saved case" if language == "en" else "Pratica salvata"
    return f"{title} {case.id[:8]} · {case.created_at.date().isoformat()}"


class ThreadCaseTask(SavedCaseChoice):
    run_id: UUID | None


class ThreadCaseTasks(ContractModel):
    items: list[ThreadCaseTask]
    next_case_id: UUID | None = None
    unbound_run_id: UUID | None = None


def list_thread_case_tasks(
    db: Session, *, thread_id: UUID, principal: Principal, language: str, after_case_id: UUID | None,
) -> ThreadCaseTasks | None:
    """Return linked cases with active run references, without their private work."""
    if db.scalar(select(AgentThread.id).where(
        AgentThread.id == str(thread_id), AgentThread.owner_subject == principal.subject,
    )) is None:
        return None
    query = active_case_links(thread_id, principal).outerjoin(AgentRunRequest, and_(
        AgentRunRequest.thread_id == str(thread_id),
        AgentRunRequest.case_id == CaseRecord.id,
        AgentRunRequest.status.in_(ACTIVE_STATUSES),
    )).add_columns(AgentRunRequest.id)
    if after_case_id is not None:
        query = query.where(CaseRecord.id > str(after_case_id))
    rows = db.execute(query.order_by(CaseRecord.id).limit(51)).all()
    items = [
        ThreadCaseTask(case_id=case.id, label=_label(case, language), run_id=run_id)
        for case, run_id in rows[:50]
    ]
    unbound = db.scalar(select(AgentRunRequest.id).where(
        AgentRunRequest.thread_id == str(thread_id), AgentRunRequest.case_id.is_(None),
        AgentRunRequest.status.in_(ACTIVE_STATUSES),
    ))
    return ThreadCaseTasks(
        items=items, next_case_id=items[-1].case_id if len(rows) > 50 else None, unbound_run_id=unbound,
    )


def resolve_saved_case(
    db: Session, *, thread_id: UUID, principal: Principal, message: StoredMessage,
    answer: AnswerResult, resume_case: bool,
) -> AnswerResult | ClarifyingQuestion:
    """Verify an explicit case or ask the owner to choose from the matching links."""
    en = message.language == "en"
    question, reply = message.clarification_question, message.clarification_reply
    if question is not None and question.procedure_goal is not None and reply is not None:
        return answer
    query = active_case_links(thread_id, principal)
    selection = answer.goal_selection
    goal = answer.goals[selection.active_goal - 1] if selection and selection.active_goal else None
    if goal is not None:
        if not goal.procedure_candidates:
            return answer
        query = query.where(CaseRecord.procedure.in_(goal.procedure_candidates))
        if goal.location_candidates and JURISDICTION not in goal.location_candidates:
            query = query.where(CaseRecord.procedure != PROCEDURE)

    normalized_text = normalize_name(message.text)
    other = OTHER_CASE_CUE.search(normalized_text) is not None
    if other and message.case_id is not None:
        query = query.where(CaseRecord.id != str(message.case_id))

    case_reply = question is not None and bool(question.case_choices) and reply is not None
    if case_reply:
        if reply.selected_case_id is None:
            return answer.model_copy(update={
                "explanation": "Choose a saved case in a new message when you are ready to continue." if en else
                "Quando vuoi continuare, scegli una pratica salvata in un nuovo messaggio.",
                "missing_information": ["case_reference"],
            })
        case = db.scalar(query.where(CaseRecord.id == str(reply.selected_case_id)))
        if case is not None:
            return _confirmed_case(answer, case, message.language)
    elif message.case_id is not None and not other:
        case = db.scalar(query.where(CaseRecord.id == str(message.case_id)))
        if case is not None:
            filing = SAVED_CASE_FILING.fullmatch(normalized_text) if resume_case else None
            if filing and not (filing["en_place"] or filing["it_place"]):
                context = read_worker_case_context(
                    db, thread_id=thread_id, case_id=message.case_id, principal=principal, lock_case=True,
                )
                if context is not None and case.archived_at is None and context.next_action == "confirm_intake":
                    return confirm_saved_intake(message.language)
            return _confirmed_case(answer, case, message.language)

    cases = db.scalars(query.order_by(CaseRecord.created_at.desc(), CaseRecord.id).limit(11)).all()
    if not cases and not case_reply and goal is not None and goal.procedure_candidates == [MARRIAGE_BANNS] and (
        "procedure" not in goal.missing_fields
    ):
        if clarification := marriage_municipality_question(message.text, message.language, goal=selection):
            return clarification
    if not cases and not resume_case and not case_reply and message.case_id is None:
        return answer
    if not cases or len(cases) > 10:
        return answer.model_copy(update={
            "explanation": (
                "Open the relevant saved case and start a new message from it." if en else
                "Apri la pratica salvata pertinente e avvia un nuovo messaggio da lì."
            ),
            "missing_information": ["case_reference"],
        })

    choices = [
        SavedCaseChoice(case_id=case.id, label=f"{number}. {_label(case, message.language)}")
        for number, case in enumerate(cases, 1)
    ]
    return ClarifyingQuestion(
        question_id=uuid4(),
        text="Which saved case do you mean?" if en else "A quale pratica salvata ti riferisci?",
        answer_shape="single_choice", options=[choice.label for choice in choices],
        missing_fields=["case_reference"], case_choices=choices, case_goal=answer.goal_selection,
    )


def _confirmed_case(answer: AnswerResult, case: CaseRecord, language: str) -> AnswerResult:
    return answer.model_copy(update={
        "explanation": (
            "The saved case choice was recorded." if language == "en" else
            "La scelta della pratica salvata è stata registrata."
        ),
        "missing_information": [field for field in answer.missing_information if field != "case_reference"],
        "selected_case": SavedCaseChoice(case_id=case.id, label=_label(case, language)),
    })
