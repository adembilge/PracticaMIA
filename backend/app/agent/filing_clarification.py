"""Ask about procedural context while filing guidance remains unverified."""

from collections.abc import Mapping, Sequence
import re
from uuid import uuid4

from app.agent.contract import AnswerResult, ClarifyingQuestion, GoalSelection, Language, NextAction
from app.knowledge.entity_matching import CatalogueName, MAX_NAME_QUERY_LENGTH, match_catalogue_names, normalize_name
from app.knowledge.service_areas import CaseLocation


MARRIAGE_BANNS = "marriage_banns"
PERMIT_RENEWAL = "residence_permit_renewal"

SAVED_CASE_FILING = re.compile(
    r"(?:(?:open|show(?: me)?) (?:the )?(?:filing|submission) (?:step|instructions) for my "
    r"(?:saved )?(?:(?P<en_place>.+) )?case|"
    r"(?:apri|mostrami) (?:il passaggio|le istruzioni) (?:di|per l) (?:invio|presentazione) "
    r"della mia pratica(?: salvat[ao])?(?: di (?P<it_place>.+))?)"
)

_BANNS = re.compile(r"\b(?:banns|pubblicazioni)\b")
_WEDDING = re.compile(r"\b(?:marry|marrying|marriage|wedding|ceremony|matrimonio|sposiamo|sposarci|cerimonia)\b")
_PLACE_END = r" (.+?)(?=\s+(?:but|and|ma|e)\b|$)"
_REPORTED_MUNICIPALITIES = {
    "residence_municipality": re.compile(
        r"\b(?:we (?:both )?(?:live|reside) in|abitiamo(?: entrambi)? ad?|risiediamo ad?)" + _PLACE_END,
    ),
    "celebration_municipality": re.compile(
        r"\b(?:we (?:will )?(?:marry|get married) in|we (?:re|are) (?:marrying|getting married) in|"
        r"ci sposiamo ad?|celebreremo il matrimonio ad?)" + _PLACE_END,
    ),
}
_RENEWAL = re.compile(r"\b(?:renew|renewing|renewal|rinnovo|rinnovi|rinnovare|rinnovando)\b")
_REPORTED_POSTAL_RENEWAL = re.compile(
    r"\b(?:(?:notice|letter) (?:says|asks|tells) (?:that |me |to )*(?:renew|renewal) "
    r"(?:by post|by mail|by postal filing)|"
    r"(?:avviso|lettera) (?:dice|chiede|indica) (?:di )?rinnovare (?:per via postale|per posta))\b"
)
_ALTERNATIVE_QUESTURA = re.compile(
    r"\b(?:(?:can|should) (?:i|we) (?:deliver|submit|take|bring) .*? (?:at|to) (?:the )?questura|"
    r"(?:posso|possiamo) (?:consegnare|presentare|portare) .*? (?:in|alla) questura)\b"
)

_PERMIT_CATEGORY = ("Which type of residence permit are you renewing?", "Che tipo di permesso di soggiorno devi rinnovare?")
_MUNICIPALITY_PROMPTS = {
    ("residence_municipality", "celebration_municipality"): (
        "In which municipality are you registered as residents, and in which municipality will you get married?",
        "In quale comune avete la residenza anagrafica e in quale si celebrerà il matrimonio?",
    ),
    ("residence_municipality",): (
        "In which municipality are you registered as residents?", "In quale comune avete la residenza anagrafica?",
    ),
    ("celebration_municipality",): (
        "In which municipality will you get married?", "In quale comune si celebrerà il matrimonio?",
    ),
}


def mentions_marriage_banns(text: str) -> bool:
    normalized = normalize_name(text)
    return bool(_BANNS.search(normalized) and _WEDDING.search(normalized))


def reports_conflicting_postal_filing(text: str) -> bool:
    normalized = normalize_name(text)
    return bool(_REPORTED_POSTAL_RENEWAL.search(normalized) and _ALTERNATIVE_QUESTURA.search(normalized))


def mentions_renewal(text: str) -> bool:
    return bool(_RENEWAL.search(normalize_name(text)))


def _unambiguous_reported_municipality(
    text: str, cue: re.Pattern[str], catalogue_names: Sequence[CatalogueName],
) -> bool:
    values = set()
    for sentence in re.split(r"[.!?;,\n]+", text):
        for mention in cue.finditer(normalize_name(sentence)):
            name = mention[1]
            if len(name) > MAX_NAME_QUERY_LENGTH:
                return False
            match = match_catalogue_names(name, list(catalogue_names), entity_type="municipality")
            if match.status != "resolved":
                return False
            values.add(match.selected_id)
    return len(values) == 1


def marriage_municipality_question(
    text: str, language: Language, *, catalogue_names: Sequence[CatalogueName] = (),
    case_locations: Mapping[str, CaseLocation] | None = None, goal: GoalSelection | None = None,
) -> ClarifyingQuestion | None:
    locations = case_locations or {}
    fields = [
        field for field in ("residence_municipality", "celebration_municipality")
        if not (field in locations and locations[field].confirmed and locations[field].municipality_id)
    ]
    if goal is None:
        fields = [
            field for field in fields
            if not _unambiguous_reported_municipality(text, _REPORTED_MUNICIPALITIES[field], catalogue_names)
        ]
    if not fields:
        return None
    return ClarifyingQuestion(
        question_id=uuid4(), text=_MUNICIPALITY_PROMPTS[tuple(fields)][0 if language == "en" else 1],
        answer_shape="free_text", missing_fields=fields, procedure_goal=goal,
    )


def permit_category_question(language: Language) -> ClarifyingQuestion:
    return ClarifyingQuestion(
        question_id=uuid4(), text=_PERMIT_CATEGORY[0 if language == "en" else 1],
        answer_shape="free_text", missing_fields=["permit_category"],
    )


def confirm_saved_intake(language: Language) -> AnswerResult:
    en = language == "en"
    return AnswerResult(
        explanation=(
            "Complete and confirm your saved case details. Then return here and ask for the filing step."
            if en else "Completa e conferma i dati della pratica salvata. Poi torna qui e chiedi come presentarla."
        ),
        verification_status="insufficient_evidence",
        missing_information=["intake_confirmation"],
        next_action=NextAction(
            label="Confirm saved case details" if en else "Conferma i dati della pratica",
            operation="confirm_saved_intake",
        ),
    )


def verify_filing_channel(language: Language, *, reported_notice: bool = False) -> AnswerResult:
    if reported_notice:
        explanation = (
            "Confirm the filing channel with the office that issued your notice before using a different channel.",
            "Prima di usare un canale diverso, chiedi all’ufficio che ha emesso l’avviso di confermare come presentare la pratica.",
        )
    else:
        explanation = (
            "I could not verify the filing channel for this case. Check the current official instructions before filing.",
            "Non ho potuto verificare il canale di presentazione per questa pratica. Controlla le istruzioni ufficiali aggiornate prima dell’invio.",
        )
    en = language == "en"
    return AnswerResult(
        explanation=explanation[0 if en else 1], verification_status="insufficient_evidence",
        next_action=NextAction(
            label="Verify the filing channel" if en else "Verifica il canale di presentazione",
            operation="verify_filing_channel",
        ),
    )
