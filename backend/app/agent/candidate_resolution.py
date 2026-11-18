"""Choose a read-only worker response when procedure routing is unresolved."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from uuid import uuid4

from app.agent.catalogue_applicability import resolve_candidate_applicability
from app.agent.checkpoints import MAX_PROCEDURE_CANDIDATES, CheckpointState
from app.agent.contract import AnswerResult, Citation, ClarifyingQuestion, NextAction, OfficialChannel
from app.agent.run_requests import StoredMessage
from app.agent.worker import RequestClarification
from app.knowledge.service_areas import CaseLocation, ServiceArea, resolve_service_areas


@dataclass(frozen=True)
class AssistanceContact:
    """A separately reviewed assistance assignment and its exact official contact page."""

    scope: ServiceArea
    citation: Citation


_QUESTIONS = {
    "intent": ("What would you like help with?", "Per cosa ti serve aiuto?"),
    "procedure": (
        "Which procedure do you need help with?", "Per quale pratica ti serve aiuto?",
    ),
    "case_reference": (
        "Which saved case would you like to resume?", "Quale pratica salvata vuoi riprendere?",
    ),
    ("location", "destination"): (
        "Which municipality are you moving to?", "In quale comune ti trasferisci?",
    ),
    ("location", "activity_location"): (
        "In which municipality does the activity take place?", "In quale comune si svolge l’attività?",
    ),
    ("date", "filing_date"): (
        "What is the filing date for this case?", "Qual è la data di presentazione della pratica?",
    ),
    ("date", "move_in_date"): ("On what date did you move in?", "In quale data ti sei trasferito o trasferita?"),
    ("circumstance", "housing_basis"): (
        "Do you own the home, rent it, or live there under another arrangement?",
        "La casa è di tua proprietà, è in affitto o ci abiti a un altro titolo?",
    ),
}
_IDENTITY_FIELDS = ("intent", "case_reference", "procedure")


def choose_candidate_step(
    message: StoredMessage, state: CheckpointState, *,
    case_locations: Mapping[str, CaseLocation], confirmed_dates: Mapping[str, date],
    confirmed_circumstances: Mapping[str, str], assignments: Sequence[ServiceArea],
    trusted_passage_ids: frozenset[str], reviewed_labels: Mapping[str, str],
    assistance_contacts: Sequence[AssistanceContact] = (),
) -> CheckpointState | RequestClarification | AnswerResult:
    """Use server-reviewed assignments and confirmed facts at a worker boundary."""
    if state.next_node != "choose_next_step":
        raise ValueError("Candidate resolution requires the choose_next_step node")

    results = resolve_candidate_applicability(
        state, case_locations=case_locations, confirmed_dates=confirmed_dates,
        confirmed_circumstances=confirmed_circumstances, assignments=tuple(assignments),
        trusted_passage_ids=trusted_passage_ids,
    )
    plausible = [procedure for procedure, result in results.items() if result.status != "unresolved"]
    separate_tasks = state.intent == "plan_multiple_tasks" and "procedure" not in state.missing_fields
    procedure_conflict = len(plausible) > 1 and not separate_tasks
    authority_conflicts = [result for result in results.values() if result.status == "ambiguous"]
    conflict = procedure_conflict or bool(authority_conflicts)
    pending = [result for result in results.values() if result.status == "needs_information"]
    language = 0 if message.language == "en" else 1
    hint = ("Possible matches include", "Tra le possibili corrispondenze ci sono")[language]

    identity_gap = next((field for field in _IDENTITY_FIELDS if field in state.missing_fields), None)
    question_field = identity_gap
    if question_field is None and procedure_conflict:
        question_field = "procedure"
    question = _QUESTIONS.get(question_field)
    if question_field is None and not conflict:
        gap = next((
            (kind, field) for result in pending
            for kind, fields in (
                ("location", result.missing_location_roles),
                ("date", result.missing_date_fields),
                ("circumstance", result.missing_circumstance_fields),
            )
            for field in fields if (kind, field) in _QUESTIONS
        ), None)
        if gap:
            question = _QUESTIONS[gap]
            question_field = gap[1]

    candidate_ids = plausible if procedure_conflict else list(results)
    if question and question_field and message.clarification_reply is None:
        prompt = question[language]
        if question_field == "procedure":
            labels = _candidate_labels(candidate_ids, reviewed_labels)
            if labels and len(details := f"{prompt} {hint} {labels}.") <= 300:
                prompt = details
        return RequestClarification(
            ClarifyingQuestion(
                question_id=uuid4(), text=prompt, answer_shape="free_text", missing_fields=[question_field],
            ),
            resume_state=state,
        )

    if not question_field and results and all(result.status == "supported" for result in results.values()):
        missing = [field for field in state.missing_fields if field != "procedure_location"]
        return state.model_copy(update={"next_node": "verify_and_respond", "missing_fields": missing})

    if conflict:
        explanation = (
            "The reviewed records point to multiple candidates.",
            "Le fonti verificate indicano più candidati.",
        )[language]
        if not procedure_conflict:
            candidate_ids = [authority for result in authority_conflicts for authority in result.authority_ids]
        if labels := _candidate_labels(candidate_ids, reviewed_labels):
            explanation += f" {hint} {labels}."
    else:
        explanation = (
            "I could not verify an applicable procedure and authority with the available information.",
            "Con le informazioni disponibili non ho potuto verificare la pratica applicabile e l’ente competente.",
        )[language]

    contacts = [
        contact.citation for contact in assistance_contacts
        if len(results) == 1 and identity_gap is None
        and contact.scope.procedure_id in results
        and contact.scope.procedure_id == contact.citation.procedure_id
        and contact.scope.evidence_ref == contact.citation.passage_id
        and contact.scope.unit_ids == (contact.citation.location_id,)
        and resolve_service_areas(
            contact.scope.procedure_id, case_locations, (contact.scope,),
            trusted_passage_ids=trusted_passage_ids, confirmed_dates=confirmed_dates,
            confirmed_circumstances=confirmed_circumstances,
        ).status == "supported"
    ]
    channel = action = None
    if len(contacts) == 1:
        citation = contacts[0]
        label = ("Ask for official assistance", "Chiedi assistenza ufficiale")[language]
        action = NextAction(label=label, operation="open_official_channel")
        channel = OfficialChannel(label=citation.publisher, url=citation.official_url)
    return AnswerResult(
        explanation=explanation,
        verification_status="conflicting_evidence" if conflict else "insufficient_evidence",
        missing_information=[question_field] if question_field else [],
        official_channel=channel, next_action=action, citations=contacts if channel else [],
    )


def _candidate_labels(candidate_ids: Sequence[str], reviewed_labels: Mapping[str, str]) -> str:
    labels = [reviewed_labels.get(candidate, "").strip() for candidate in candidate_ids]
    unique_labels = list(dict.fromkeys(label for label in labels if 0 < len(label) <= 120))
    return ", ".join(unique_labels[:MAX_PROCEDURE_CANDIDATES])
