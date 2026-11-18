"""Read-only intent extraction against a server-supplied reviewed catalogue."""

from collections.abc import Sequence
from dataclasses import dataclass
import re
from typing import Literal
import unicodedata

from app.agent.checkpoints import CheckpointState, MAX_PROCEDURE_CANDIDATES
from app.agent.contract import AgentIntent
from app.agent.run_requests import StoredMessage
from app.knowledge.entity_matching import (
    CatalogueName, MAX_NAME_QUERY_LENGTH, NameMatchResult, match_catalogue_names, normalize_name,
)

MissingContext = Literal["intent", "procedure", "procedure_location", "case_reference"]
_PLACE_TYPES = ("municipality", "province", "region")

# Narrow bilingual cues for the first internal step. Exact catalogue mentions
# cover bare procedure names. Query expansion and noisy text are a separate step.
_INTENT_CUES: tuple[tuple[AgentIntent, re.Pattern[str]], ...] = (
    ("plan_multiple_tasks", re.compile(
        r"\b(?:plan several tasks|multiple procedures|piu pratiche)\b"
    )),
    ("resume_case", re.compile(
        r"\b(?:(?:resume|continue) (?:(?:my|the|this) )?(?:case|application)|"
        r"pick up (?:my|our|where)|riprendere (?:la|il)|riprendi (?:la|il)|"
        r"continua(?:re)? (?:la|il) mi[ao] (?:pratica|caso))\b"
    )),
    ("explain_form_field", re.compile(
        r"\b(?:form field|field on (?:the|this) form|field in (?:the|this) form|"
        r"(?:mean|enter|put|write|fill in) .* (?:form|field)|"
        r"campo (?:del|nel) modulo|(?:significa|scrivo|inserisco|compilo) .* (?:modulo|campo))\b"
    )),
    ("explain_notice", re.compile(
        r"\b(?:what does .* (?:letter|notice|communication)|"
        r"(?:explain|understand) .* (?:letter|notice|communication)|"
        r"(?:significa|spiegami|capire) .* (?:lettera|avviso|comunicazione))\b"
    )),
    ("request_information", re.compile(
        r"\b(?:what (?:is|are|does)|which documents|how much|"
        r"cosa (?:e|sono|significa)|che cosa (?:e|sono|significa)|quali documenti|quanto costa)\b"
    )),
    ("find_procedure", re.compile(
        r"\b(?:how (?:do|can) i|where (?:do|can) i|find (?:the|a) procedure|"
        r"come (?:faccio|posso|comunico|presento|richiedo)|dove (?:posso|presento)|da dove inizio)\b"
    )),
)


@dataclass(frozen=True)
class CatalogueMention:
    expression: str
    match: NameMatchResult


@dataclass(frozen=True)
class IntentExtraction:
    intent: AgentIntent | None
    mentions: tuple[CatalogueMention, ...]
    procedure_candidates: tuple[str, ...]
    missing_context: tuple[MissingContext, ...]


def _catalogue_mentions(
    text: str, catalogue_names: Sequence[CatalogueName],
) -> tuple[CatalogueMention, ...]:
    # Index names by their exact folded terms. Looking only at message windows
    # avoids a separate scan of the whole catalogue for each possible mention.
    names: dict[tuple[str, ...], list[CatalogueName]] = {}
    for record in catalogue_names:
        if not record.approved_for_search or not record.evidence_ref.strip():
            continue
        key = tuple(normalize_name(record.name).split())
        if key and len(record.name) <= MAX_NAME_QUERY_LENGTH:
            names.setdefault(key, []).append(record)

    text = unicodedata.normalize("NFC", text)
    tokens = list(re.finditer(r"[^\W_]+", text))
    words = [normalize_name(token.group()) for token in tokens]
    max_width = max(map(len, names), default=0)
    mentions = []
    start = 0
    while start < len(tokens):
        for end in range(min(start + max_width, len(tokens)), start, -1):
            records = names.get(tuple(words[start:end]))
            if not records:
                continue
            expression = text[tokens[start].start():tokens[end - 1].end()]
            if len(expression) > MAX_NAME_QUERY_LENGTH:
                continue
            # A longer authority name owns its span. For example, a city inside
            # an issuer's name is not a separate place expression.
            mentions.append(CatalogueMention(expression, match_catalogue_names(expression, records)))
            start = end
            break
        else:
            start += 1
    return tuple(mentions)


def extract_intent(
    message: StoredMessage, *, catalogue_names: Sequence[CatalogueName],
) -> IntentExtraction:
    """Return hypotheses and context gaps, leaving scope and case data untouched."""
    mentions = _catalogue_mentions(message.text, catalogue_names)
    procedures = tuple(dict.fromkeys(
        candidate.catalogue_id
        for mention in mentions
        for candidate in mention.match.candidates
        if candidate.entity_type == "procedure"
    ))
    resolved_procedures = {
        mention.match.selected_id for mention in mentions if mention.match.selected_type == "procedure"
    }
    normalized_text = normalize_name(message.text)
    intent = next((label for label, cue in _INTENT_CUES if cue.search(normalized_text)), None)
    if intent in (None, "find_procedure") and len(resolved_procedures) > 1:
        intent = "plan_multiple_tasks"
    elif intent is None and procedures:
        intent = "find_procedure"

    missing: list[MissingContext] = []
    if intent is None:
        missing.append("intent")
    if intent == "request_information" and len(resolved_procedures) < len(procedures):
        missing.append("procedure")
    if intent in ("find_procedure", "plan_multiple_tasks"):
        required_procedures = 2 if intent == "plan_multiple_tasks" else 1
        if len(resolved_procedures) < max(required_procedures, len(procedures)):
            missing.append("procedure")
        locations = {
            (candidate.entity_type, candidate.catalogue_id)
            for mention in mentions
            for candidate in mention.match.candidates
            if candidate.entity_type in _PLACE_TYPES
        }
        resolved_location = len(locations) == 1 and any(
            mention.match.selected_type in _PLACE_TYPES for mention in mentions
        )
        if not resolved_location:
            missing.append("procedure_location")
    if intent == "resume_case" and message.case_context is None:
        missing.append("case_reference")
    return IntentExtraction(intent, mentions, procedures, tuple(missing))


def identify_intent_step(
    message: StoredMessage, state: CheckpointState, *, catalogue_names: Sequence[CatalogueName],
) -> CheckpointState:
    """Project the result onto the worker checkpoint without keeping message spans."""
    if state.next_node != "identify_intent":
        raise ValueError("Intent extraction requires the identify_intent node")
    result = extract_intent(message, catalogue_names=catalogue_names)
    procedures = list(result.procedure_candidates)
    missing = list(result.missing_context)
    if len(procedures) > MAX_PROCEDURE_CANDIDATES:
        # The checkpoint cannot retain all plausible records. Ask for a more
        # specific procedure instead of dropping candidates according to order.
        procedures = []
        if "procedure" not in missing:
            missing.append("procedure")
    evidence_ready = (
        not missing and len(procedures) == 1
        and result.intent in ("find_procedure", "request_information")
    )
    return CheckpointState(
        next_node="find_evidence" if evidence_ready else "choose_next_step",
        intent=result.intent, procedure_candidates=procedures, missing_fields=missing,
    )
