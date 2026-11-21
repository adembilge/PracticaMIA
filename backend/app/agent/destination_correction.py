"""Recognise explicit destination corrections in a new message."""

from dataclasses import dataclass
from datetime import datetime, timezone
import re

from app.agent.contract import AnswerResult, Language, NextAction


_CORRECTION = {
    "en": re.compile(
        r"correction\s*:\s*(?:(?:my|the) )?destination(?: municipality)? is (?:the municipality of )?"
        r"([^.!?\r\n]+)(?:\.\s+[^.!?\r\n]+ is my previous municipality)?\.?", re.I,
    ),
    "it": re.compile(
        r"correzione\s*:\s*(?:il )?comune di destinazione (?:è|e) "
        r"([^.!?\r\n]+)(?:\.\s+[^.!?\r\n]+ (?:è|e) il comune precedente)?\.?", re.I,
    ),
}


def destination_correction_name(text: str, language: Language) -> str | None:
    match = _CORRECTION[language].fullmatch(text.strip())
    if match is None:
        return None
    return match[1].strip() or None


@dataclass(frozen=True)
class DestinationCorrection:
    """The revision and time of a correction carried in an encrypted request."""

    revision: int
    accepted_at: datetime

    def needs_confirmation(self, confirmed_at: datetime | None) -> bool:
        if confirmed_at is None:
            return True
        confirmed_at = confirmed_at.replace(tzinfo=timezone.utc) if confirmed_at.tzinfo is None else confirmed_at
        return confirmed_at <= self.accepted_at


def reassess_destination(language: Language) -> AnswerResult:
    en = language == "en"
    return AnswerResult(
        explanation=(
            "Review and confirm the destination municipality here in the conversation. "
            "I could not verify filing instructions for the corrected destination."
            if en else
            "Rivedi e conferma il comune di destinazione qui nella conversazione. "
            "Non ho potuto verificare le istruzioni di invio per la destinazione corretta."
        ),
        verification_status="insufficient_evidence",
        next_action=NextAction(
            label="Review the corrected destination" if en else "Rivedi la destinazione corretta",
            operation="reassess_destination",
        ),
    )
