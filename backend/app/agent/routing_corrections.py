"""Translate an answer to the recorded question into bounded routing inputs."""

from collections.abc import Sequence
from datetime import date
import re

from app.agent.checkpoints import CheckpointState, RoutingCorrections
from app.agent.contract import Language
from app.agent.run_requests import StoredMessage
from app.knowledge.entity_matching import CatalogueName, MAX_NAME_QUERY_LENGTH, match_catalogue_names, normalize_name
from app.private_documents.intelligence import HOUSING_VALUES, normalize_labeled_move_date

_DISPLAY_HOUSING = (
    {
        "I own the home": "owner", "I rent under a registered private agreement": "registered_private_rental",
        "I rent under a different arrangement": "other", "I live there as a guest": "guest",
        "Another arrangement": "other",
    },
    {
        "La casa è di mia proprietà": "owner", "Ho un contratto di locazione privata registrato": "registered_private_rental",
        "Ho un altro tipo di affitto": "other", "Ci abito come ospite": "guest", "Un altro titolo": "other",
    },
)
_DISPLAY_CITIZENSHIP = {
    "en": {"Italian": "italian", "Non-Italian": "non_italian"},
    "it": {"Italiana": "italian", "Non italiana": "non_italian"},
}
ROUTING_FIELD_LABELS = {
    "destination": ("the destination municipality", "il comune di destinazione"),
    "activity_location": ("the municipality where the activity takes place", "il comune in cui si svolge l’attività"),
    "filing_date": ("the filing date", "la data di presentazione"),
    "move_in_date": ("the move-in date", "la data del trasferimento"),
    "housing_basis": ("the housing arrangement", "il titolo di occupazione"),
    "citizenship_class": ("the citizenship category", "la categoria di cittadinanza"),
}
_NAME_FIELDS = {"procedure", "destination", "activity_location"}
_DESTINATION_REPLY = {
    "en": re.compile(r"(?:the )?destination(?: municipality)? is (?:the municipality of )?([^.!?\r\n]+)\.?", re.I),
    "it": re.compile(r"(?:il )?comune di destinazione (?:è|e) ([^.!?\r\n]+)\.?", re.I),
}


def housing_options(language: Language) -> list[str]:
    return list(_DISPLAY_HOUSING[0 if language == "en" else 1])


def citizenship_options(language: Language) -> list[str]:
    return list(_DISPLAY_CITIZENSHIP[language])


def apply_routing_reply(
    message: StoredMessage, state: CheckpointState, catalogue_names: Sequence[CatalogueName],
) -> CheckpointState:
    question, reply = message.clarification_question, message.clarification_reply
    if question is None or reply is None or not reply.text or reply.disposition != "answer":
        return state
    if question.question_id != reply.question_id:
        return state

    updates = {}
    for field, value in _requested_values(reply.text, question.missing_fields).items():
        if field in ("move_in_date", "filing_date"):
            if normalized := normalize_labeled_move_date(value):
                updates[field] = date.fromisoformat(normalized)
        elif field == "housing_basis":
            options = _DISPLAY_HOUSING[0 if message.language == "en" else 1]
            if housing := options.get(value) or HOUSING_VALUES.get(value.casefold()):
                updates[field] = housing
        elif field == "citizenship_class":
            options = _DISPLAY_CITIZENSHIP[message.language]
            citizenship = value.casefold().replace("-", " ").replace("_", " ")
            for label, category in options.items():
                if citizenship in (label.casefold().replace("-", " "), category.replace("_", " ")):
                    updates[field] = category
                    break
        elif field in _NAME_FIELDS:
            if field == "destination" and (sentence := _DESTINATION_REPLY[message.language].fullmatch(value)):
                value = sentence[1].strip()
            if len(value) > MAX_NAME_QUERY_LENGTH or not normalize_name(value):
                continue
            match = match_catalogue_names(
                value, list(catalogue_names), entity_type="procedure" if field == "procedure" else "municipality",
            )
            if match.status == "resolved":
                updates[field] = match.selected_id
    if not updates:
        return state

    previous = state.routing_corrections or RoutingCorrections()
    procedure = updates.get("procedure")
    if procedure and procedure != previous.procedure:
        previous = RoutingCorrections()
    corrections = RoutingCorrections.model_validate({
        **previous.model_dump(), **updates,
        "reply_event_seqs": previous.reply_event_seqs | dict.fromkeys(updates, reply.event_seq),
    })
    return state.model_copy(update={
        "routing_corrections": corrections,
        "procedure_candidates": [procedure] if procedure else state.procedure_candidates,
        "missing_fields": [field for field in state.missing_fields if field not in updates],
        "evidence_ids": [],
    })


def _requested_values(text: str, fields: list[str]) -> dict[str, str]:
    if len(fields) == 1:
        return {fields[0]: text}
    labels = {
        _label_key(label): field
        for field in fields
        for label in (field, *ROUTING_FIELD_LABELS.get(field, ()))
    }
    values: dict[str, set[str]] = {}
    for line in text.splitlines():
        label, separator, value = line.partition(":")
        if separator and (field := labels.get(_label_key(label))) and value.strip():
            values.setdefault(field, set()).add(value.strip())
    return {field: next(iter(options)) for field, options in values.items() if len(options) == 1}


def _label_key(label: str) -> str:
    return normalize_name(label).removeprefix("the ").removeprefix("il ").removeprefix("la ")
