"""Interpret explicit replies without treating uncertainty as a case fact."""

from app.agent.contract import ClarificationDisposition, ClarificationReply, ClarifyingQuestion
from app.knowledge.entity_matching import normalize_name

_SHORT_REPLIES: dict[str, ClarificationDisposition] = {
    "i don t know": "unknown",
    "i do not know": "unknown",
    "i m not sure": "unknown",
    "i am not sure": "unknown",
    "not sure": "unknown",
    "non lo so": "unknown",
    "non saprei": "unknown",
    "non sono sicuro": "unknown",
    "non sono sicura": "unknown",
    "skip for now": "skip",
    "salta per ora": "skip",
    "change topic": "change_topic",
    "cambia argomento": "change_topic",
}


def resolve_disposition(reply: ClarificationReply, question: ClarifyingQuestion) -> ClarificationDisposition:
    if reply.text is None or reply.text in question.options:
        return reply.disposition
    return _SHORT_REPLIES.get(normalize_name(reply.text), "answer")
