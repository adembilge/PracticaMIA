"""Open the exact current passage behind a card in an owned terminal answer."""

import re
from uuid import UUID

from sqlalchemy.orm import Session

from app.agent.catalogue_evidence import catalogue_passage
from app.agent.contract import ContractModel, Language, ShortText
from app.agent.run_events import read_run_snapshot
from app.agent.run_requests import read_run_message
from app.agent.tool_contract import CataloguePassage
from app.auth.tokens import Principal
from app.knowledge.search import resolve_approved_passage


# Plain-language descriptions for the residence-change vocabulary of the pilot.
_TERMS = {
    "cambio di residenza": {
        "en": "Updating the address recorded for your registered residence.",
        "it": "Aggiornamento dell’indirizzo della residenza registrata.",
    },
    "contratto di locazione": {
        "en": "A rental agreement between the landlord and the tenant.",
        "it": "Accordo di affitto tra il locatore e l’inquilino.",
    },
    "anagrafe": {
        "en": "The municipal population register or the office that manages it.",
        "it": "Il registro della popolazione del Comune o l’ufficio che lo gestisce.",
    },
    "residenza": {
        "en": "Registered residence, the address recorded in the municipal register.",
        "it": "La residenza all’indirizzo registrato nell’anagrafe comunale.",
    },
}
_TERM_PATTERN = re.compile(r"\b(?ai:" + "|".join(map(re.escape, _TERMS)) + r")\b")


class TermExplanation(ContractModel):
    term: ShortText
    explanation: ShortText


class RunSourceCard(ContractModel):
    title: ShortText
    source_language: Language
    explanation_language: Language
    passage: CataloguePassage
    terms: list[TermExplanation]


def _explain_terms(text: str, language: Language) -> list[TermExplanation]:
    seen = set()
    terms = []
    for match in _TERM_PATTERN.finditer(text):
        original = match.group()
        term = original.casefold()
        if term not in seen:
            seen.add(term)
            terms.append(TermExplanation(term=original, explanation=_TERMS[term][language]))
    return terms


def read_run_source_card(
    db: Session, *, thread_id: UUID, run_id: UUID, citation_id: str, principal: Principal, key: bytes,
) -> RunSourceCard | None:
    context = {"thread_id": thread_id, "run_id": run_id, "principal": principal, "key": key}
    snapshot = read_run_snapshot(db, **context)
    if snapshot is None or snapshot.result is None:
        return None
    saved = next((citation for citation in snapshot.result.citations if citation.citation_id == citation_id), None)
    if saved is None:
        return None
    approved = resolve_approved_passage(
        db, citation_id=citation_id, jurisdiction=saved.location_id, procedure_id=saved.procedure_id, language=None,
    )
    if approved is None:
        return None
    passage = catalogue_passage(approved)
    if passage.citation != saved:
        return None
    message = read_run_message(db, **context)
    if message is None:
        return None
    return RunSourceCard(
        title=approved.title, source_language=approved.language, explanation_language=message.language,
        passage=passage, terms=_explain_terms(passage.content, message.language),
    )
