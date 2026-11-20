"""Identify an unreadable appointment date or attachment name in a notice."""

import re
from typing import Literal

from app.knowledge.entity_matching import normalize_name


NoticeField = Literal["appointment_date", "attachment_name"]
_NOTICE = re.compile(r"\b(?:notice|summons|letter|communication|avviso|convocazione|lettera|comunicazione)\b")
_APPOINTMENT = re.compile(r"\b(?:appointment|summons|appuntamento|convocazione)\b")
_ATTACHMENT = re.compile(r"\b(?:attachments?|allegat[oi])\b")
_DATE = re.compile(r"\b(?:date|data)\b")
_ATTACHMENT_NAME = re.compile(r"\b(?:name|nome|which attachments?|qual[ei] allegat[oi])\b")
_UNREADABLE = re.compile(
    r"\b(?:unreadable|illegible|smudged|cropped|cuts? off|can t read|cannot read|"
    r"illeggibile|taglia|tagliat[oa]|non (?:riesco a leggere|si legge))\b"
)
_NEGATED_DAMAGE = re.compile(
    r"\b(?:not (?:unreadable|illegible|smudged|cropped)|non e (?:illeggibile|tagliat[oa]))\b"
)


def unreadable_notice_field(text: str) -> NoticeField | None:
    normalized = normalize_name(text)
    if not _NOTICE.search(normalized):
        return None

    mentions_appointment = _APPOINTMENT.search(normalized)
    mentions_attachment = _ATTACHMENT.search(normalized)
    for sentence in re.split(r"[.!?;\n]+", text):
        clause = normalize_name(sentence)
        if not _UNREADABLE.search(clause) or _NEGATED_DAMAGE.search(clause):
            continue
        appointment_in_scope = _APPOINTMENT.search(clause) or (
            mentions_appointment and not _ATTACHMENT.search(clause)
        )
        if appointment_in_scope and _DATE.search(clause):
            return "appointment_date"
        if mentions_attachment and _ATTACHMENT_NAME.search(clause):
            return "attachment_name"
    return None
