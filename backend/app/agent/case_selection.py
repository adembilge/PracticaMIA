"""Resolve an owned saved-case reference without changing a run's case binding."""

import re
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.agent.contract import AnswerResult, ClarifyingQuestion, SavedCaseChoice
from app.agent.run_requests import StoredMessage
from app.agent.threads import active_case_links
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


def resolve_saved_case(
    db: Session, *, thread_id: UUID, principal: Principal, message: StoredMessage,
    answer: AnswerResult, resume_case: bool,
) -> AnswerResult | ClarifyingQuestion:
    """Verify an explicit case or ask the owner to choose from the matching links."""
    en = message.language == "en"
    query = active_case_links(thread_id, principal)
    if answer.goal_selection and answer.goal_selection.active_goal:
        goal = answer.goals[answer.goal_selection.active_goal - 1]
        if not goal.procedure_candidates:
            return answer
        query = query.where(CaseRecord.procedure.in_(goal.procedure_candidates))
        if goal.location_candidates and JURISDICTION not in goal.location_candidates:
            query = query.where(CaseRecord.procedure != PROCEDURE)

    other = OTHER_CASE_CUE.search(normalize_name(message.text)) is not None
    if other and message.case_id is not None:
        query = query.where(CaseRecord.id != str(message.case_id))

    question, reply = message.clarification_question, message.clarification_reply
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
            return _confirmed_case(answer, case, message.language)

    cases = db.scalars(query.order_by(CaseRecord.created_at.desc(), CaseRecord.id).limit(11)).all()
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
