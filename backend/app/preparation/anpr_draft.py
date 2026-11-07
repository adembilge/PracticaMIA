"""Version-cited ANPR field transcription draft for one synthetic Milan tenant case.

This is a structured preparation worksheet, NOT an official form, eligibility
decision, or a claim that the ANPR portal accepts these exact fields today.
The approved administrative rules catalog remains a separate control.
"""
from __future__ import annotations

from datetime import date
import re

from app.preparation.intake import scope_intake

OFFICIAL_MILAN_URL = "https://www.comune.milano.it/servizi/anagrafe/cambio-di-residenza"
ANPR_GUIDE_URL = (
    "https://public-anpr.github.io/anpr-docs-cittadino/"
    "src/docs/guide/guida_compilazione_cambio_residenza.pdf"
)

# These values are a transcription aid from the public ANPR documentation
# edition inspected on 2026-11-07, not a replacement for live portal fields.
FIELDS = (
    ("family", "family_relationship", "Relationship to household head",
     "Parentela con intestatario scheda", True, "text", "p. 7"),
    ("family", "driving_licence_yes_no", "Driving licence (yes or no)",
     "Patente (sì o no)", True, "yes_no", "p. 7"),
    ("family", "vehicles_yes_no", "Vehicles (yes or no)",
     "Autoveicoli (sì o no)", True, "yes_no", "p. 7"),
    ("residence", "street_address", "Street address (Via/Piazza and name)",
     "Indirizzo (es. Via Roma)", True, "text", "p. 8"),
    ("residence", "civic_number", "Street number",
     "Numero civico", True, "text", "p. 8"),
    ("residence", "postal_code", "Postal code (CAP)",
     "Codice postale (CAP)", True, "cap", "p. 8"),
    ("residence", "localita", "Locality (optional)",
     "Località (facoltativa)", False, "text", "p. 8"),
    ("residence", "scala_piano_interno", "Staircase, floor and unit (optional)",
     "Scala, piano, interno (facoltativi)", False, "text", "p. 8"),
    ("housing", "rental_registration_office_municipality",
     "Municipality of the Revenue Agency registration office",
     "Comune della sede dell'Agenzia delle Entrate", True, "text", "p. 12"),
    ("housing", "rental_contract_date",
     "Rental contract date (as worded in the guide)",
     "Data del contratto di locazione (come nella guida)", True, "date", "p. 12"),
    ("housing", "rental_registration_number",
     "Rental contract registration number",
     "Numero di registrazione del contratto", True, "text", "p. 12"),
    ("contact", "contact_phone", "Contact telephone (if provided)",
     "Telefono di contatto (se indicato)", False, "text", "pp. 14-15"),
    ("contact", "contact_phone_2", "Second contact telephone (optional)",
     "Secondo recapito telefonico (facoltativo)", False, "text", "pp. 14-15"),
    ("contact", "inspection_availability", "Availability for address check",
     "Fascia oraria di reperibilità", False, "text", "pp. 14-15"),
)

SECTIONS = (
    ("family", "Household information", "Informazioni famiglia"),
    ("residence", "New residence", "Nuova residenza"),
    ("housing", "Registered rental", "Locazione registrata"),
    ("contact", "Contact details", "Dati di contatto"),
)

def _valid(kind: str, value: str) -> bool:
    if not value or len(value) > 180 or any(ord(c) < 32 for c in value):
        return False
    if kind == "yes_no":
        return value in ("yes", "no")
    if kind == "cap":
        return bool(re.fullmatch(r"[0-9]{5}", value))
    if kind == "date":
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            return False
        try:
            date.fromisoformat(value)
        except ValueError:
            return False
    return True


def build_anpr_draft(facts: dict) -> dict:
    """Return only whitelisted, confirmed field values; never auto-submit."""
    intake = scope_intake(facts)
    in_scope = intake["status"] == "candidate_scope_complete"
    sections = []
    missing = []
    for section, title_en, title_it in SECTIONS:
        fields = []
        for owner, key, label_en, label_it, required, kind, page in FIELDS:
            if owner != section:
                continue
            raw = facts.get(key)
            value = raw.strip() if isinstance(raw, str) else ""
            valid = _valid(kind, value) if value else False
            if in_scope and required and not valid:
                missing.append(key)
            fields.append({
                "key": key, "label_en": label_en, "label_it": label_it,
                "value": value if valid else "",
                "required_in_inspected_guide": required,
                "input_kind": kind, "valid": valid,
                "guide_page": page,
            })
        sections.append({
            "id": section, "title_en": title_en, "title_it": title_it,
            "fields": fields,
        })
    if intake["status"] == "outside_first_candidate":
        state = "outside_first_candidate"
    elif not in_scope:
        state = "needs_scope_information"
    elif missing:
        state = "needs_field_information"
    else:
        state = "field_transcription_complete"
    return {
        "artifact_type": "synthetic_anpr_field_transcription_draft",
        "simulation_only": True,
        "official_form": False,
        "legal_eligibility_assessed": False,
        "ruleset_activated": False,
        "government_submission_status": "NOT_SUBMITTED",
        "state": state,
        "source_edition": "public_anpr_documentation_guide_unverified_currentness",
        "source_url": ANPR_GUIDE_URL,
        "source_sections": "1.1.1-1.1.6; public documentation PDF, 29 pages",
        "source_pdf_sha256_inspected": "7ecc161913692a6d6102931c1b8cba368647a69ce664fd682785cdfd5fbadd81",
        "source_pdf_metadata_creation_date": "2025-04-08",
        "source_registry_approved": False,
        "source_currentness_verified": False,
        "scope": intake["status"],
        "confirmed_fixed_selections": {
            "destination_province": "MI",
            "destination_municipality": "Milano",
            "housing_title_in_inspected_guide": "option_2_registered_rental",
        } if in_scope else {},
        "sections": sections,
        "missing_fields": missing,
        "guide_notes": [
            "The public ANPR guide may not match the current live form.",
            "Select the applicant yourself in the ANPR portal.",
            "The inspected guide §1.1.5 (printed pages 15–16) describes "
            "supporting attachments as generally optional for this scenario; "
            "PDF/JPG/PNG and 1 MB per file refer to this 2025 edition only.",
            "The inspected guide uses §1.1.4 for contact data and §1.1.5 for uploads.",
            "Only the applicant can log in, review and submit on ANPR.",
            "TARI is a separate municipal declaration.",
        ],
        "official_handoff": {
            "title": "Comune di Milano — cambio di residenza",
            "url": OFFICIAL_MILAN_URL,
            "user_only": True,
        },
    }
