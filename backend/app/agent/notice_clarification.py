"""Identify an unreadable appointment date or attachment name in a notice."""

import re
from typing import Literal

from app.knowledge.entity_matching import normalize_name


NoticeField = Literal["appointment_date", "attachment_name"]
_NOTICE = re.compile(r"\b(?:notice|summons|letter|communication|avviso|convocazione|lettera|comunicazione)\b")
_APPOINTMENT = re.compile(r"\b(?:appointment|summons|appuntamento|convocazione)\b")
_ATTACHMENT = re.compile(r"\b(?:attachments?|allegat[oi])\b")
_DATE = re.compile(r"\b(?:date|data)\b")
_ATTACHMENT_NAME = re.compile(r"\b(?:name|nome)\b")
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

    for sentence in re.split(r"[.!?;\n]+", text):
        clause = normalize_name(sentence)
        if not _UNREADABLE.search(clause) or _NEGATED_DAMAGE.search(clause):
            continue
        appointment_in_scope = _APPOINTMENT.search(clause) or (
            not _ATTACHMENT.search(clause) and _APPOINTMENT.search(normalized)
        )
        if appointment_in_scope and _DATE.search(clause):
            return "appointment_date"
        attachment_in_scope = _ATTACHMENT.search(clause) and not _DATE.search(clause)
        named_attachment_in_scope = _ATTACHMENT_NAME.search(clause) and _ATTACHMENT.search(normalized)
        if attachment_in_scope or named_attachment_in_scope:
            return "attachment_name"
    return None
