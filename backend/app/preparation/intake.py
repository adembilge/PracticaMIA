"""Synthetic intake for the first *proposed* Milan route.

This is a product-scope questionnaire, NOT an eligibility evaluator.
The candidate is pending municipal review.  In particular, matching every
field must not unlock requirements, a checklist, or an application package.
Only the separately approved, versioned rules engine can do that.
"""
from __future__ import annotations

from typing import Any

QUESTIONS: tuple[dict[str, Any], ...] = (
    {
        "field": "citizenship_class",
        "expected": "italian",
        "label_en": "Which example citizenship category applies?",
        "label_it": "Quale categoria di cittadinanza si applica all'esempio?",
        "options": (
            {"value": "italian", "label_en": "Italian", "label_it": "Italiana"},
            {"value": "non_italian", "label_en": "Other citizenship", "label_it": "Altra cittadinanza"},
            {"value": "unknown", "label_en": "Not known", "label_it": "Non so"},
        ),
    },
    {
        "field": "registration_context",
        "expected": "already_registered_in_italy",
        "label_en": "Was this fictional applicant already registered as a resident in Italy?",
        "label_it": "La persona fittizia era già residente registrata in Italia?",
        "options": (
            {"value": "already_registered_in_italy", "label_en": "Yes", "label_it": "Sì"},
            {"value": "arrival_from_abroad", "label_en": "Arriving from abroad", "label_it": "Arrivo dall'estero"},
            {"value": "unknown", "label_en": "Not known", "label_it": "Non so"},
        ),
    },
    {
        "field": "destination_municipality",
        "expected": "milano",
        "label_en": "Which municipality is this fictional move to?",
        "label_it": "In quale comune avviene il trasferimento fittizio?",
        "options": (
            {"value": "milano", "label_en": "Milano", "label_it": "Milano"},
            {"value": "other", "label_en": "Another municipality", "label_it": "Altro comune"},
            {"value": "unknown", "label_en": "Not known", "label_it": "Non so"},
        ),
    },
    {
        "field": "household_scope",
        "expected": "individual_no_aggregation",
        "label_en": "How is the fictional applicant moving?",
        "label_it": "Come si trasferisce la persona fittizia?",
        "options": (
            {"value": "individual_no_aggregation", "label_en": "Individually, not joining a household", "label_it": "Da sola, senza unirsi a un nucleo esistente"},
            {"value": "joining_household", "label_en": "Joining an existing household", "label_it": "Entra in un nucleo esistente"},
            {"value": "multi_person", "label_en": "Several applicants", "label_it": "Più richiedenti"},
            {"value": "unknown", "label_en": "Not known", "label_it": "Non so"},
        ),
    },
)


def validate_scope_facts(facts: dict[str, Any]) -> bool:
    """Do not accept invented routing choices as valid user-confirmed facts."""
    for question in QUESTIONS:
        if question["field"] not in facts:
            continue
        value = facts[question["field"]]
        if not isinstance(value, str) or value not in {
            opt["value"] for opt in question["options"]
        }:
            return False
    return True


def scope_intake(facts: dict[str, Any]) -> dict[str, Any]:
    """Ask the first unresolved question; flag exclusions as *product scope* only."""
    for index, question in enumerate(QUESTIONS):
        value = facts.get(question["field"])
        public_question = {
            "field": question["field"],
            "label_en": question["label_en"],
            "label_it": question["label_it"],
            "options": list(question["options"]),
        }
        if value is None or value == "" or value == "unknown":
            return {
                "status": "needs_information",
                "answered_count": index,
                "total_questions": len(QUESTIONS),
                "next_question": public_question,
                "excluded_by": None,
                "is_legal_assessment": False,
            }
        if not isinstance(value, str) or value not in {
            option["value"] for option in question["options"]
        }:
            return {
                "status": "invalid_input",
                "answered_count": index,
                "total_questions": len(QUESTIONS),
                "next_question": public_question,
                "excluded_by": None,
                "is_legal_assessment": False,
            }
        if value != question["expected"]:
            return {
                "status": "outside_first_candidate",
                "answered_count": index + 1,
                "total_questions": len(QUESTIONS),
                "next_question": None,
                "excluded_by": question["field"],
                "is_legal_assessment": False,
            }
    return {
        "status": "candidate_scope_complete",
        "answered_count": len(QUESTIONS),
        "total_questions": len(QUESTIONS),
        "next_question": None,
        "excluded_by": None,
        "is_legal_assessment": False,
    }
