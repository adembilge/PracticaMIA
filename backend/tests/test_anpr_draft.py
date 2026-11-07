"""Offline regression for narrow Milan tenant field transcription.

Tests do not claim the public ANPR guide is current or legally approved.
"""
from copy import deepcopy
from app.preparation.anpr_draft import build_anpr_draft
from app.preparation.intake import QUESTIONS


def scope():
    return {q["field"]: q["expected"] for q in QUESTIONS}


def complete_fields():
    return {
        "family_relationship": "intestatario scheda",
        "driving_licence_yes_no": "no",
        "vehicles_yes_no": "yes",
        "street_address": "Via Synthetic Example",
        "civic_number": "10",
        "postal_code": "20121",
        "rental_registration_office_municipality": "Milano",
        "rental_contract_date": "2026-01-15",
        "rental_registration_number": "TEST-12345",
    }


def test_missing_scope_cannot_claim_complete_preparation():
    result = build_anpr_draft({})
    assert result["state"] == "needs_scope_information"
    assert result["confirmed_fixed_selections"] == {}
    assert result["simulation_only"] is True
    assert result["government_submission_status"] == "NOT_SUBMITTED"
    assert result["official_form"] is False


def test_complete_candidate_scope_requires_actual_manual_fields():
    result = build_anpr_draft(scope())
    assert result["state"] == "needs_field_information"
    assert len(result["missing_fields"]) == 9
    assert result["confirmed_fixed_selections"]["destination_province"] == "MI"
    assert result["ruleset_activated"] is False
    assert result["source_currentness_verified"] is False


def test_field_transcription_complete_is_not_government_approval():
    facts = {**scope(), **complete_fields(), "contact_phone": "+39 123456"}
    result = build_anpr_draft(facts)
    assert result["state"] == "field_transcription_complete"
    assert result["missing_fields"] == []
    assert result["government_submission_status"] == "NOT_SUBMITTED"
    assert result["legal_eligibility_assessed"] is False
    assert result["official_form"] is False
    assert result["official_handoff"]["user_only"] is True
    values = {f["key"]: f["value"] for s in result["sections"] for f in s["fields"]}
    assert values["postal_code"] == "20121"
    assert values["rental_contract_date"] == "2026-01-15"
    assert "citizenship_class" not in values


def test_out_of_scope_even_with_all_fields_never_claims_complete():
    facts = {**scope(), **complete_fields(), "housing_basis": "owner"}
    result = build_anpr_draft(facts)
    assert result["state"] == "outside_first_candidate"
    assert result["confirmed_fixed_selections"] == {}


def test_invalid_dates_and_cap_cannot_claim_field_transcription_complete():
    bad = {**scope(), **complete_fields(),
           "postal_code": "2012", "rental_contract_date": "2026-02-30"}
    result = build_anpr_draft(bad)
    assert result["state"] == "needs_field_information"
    assert {"postal_code", "rental_contract_date"}.issubset(result["missing_fields"])


def test_no_unrecognized_or_unsupported_fields_enter_export():
    facts = {**scope(), **complete_fields(),
             "fake_admin_approval": "yes",
             "personal_identifier": "DO-NOT-EXPORT",
             "street_address": "Via Synthetic Example"}
    result = build_anpr_draft(facts)
    assert "DO-NOT-EXPORT" not in repr(result)
    assert "fake_admin_approval" not in repr(result)
    assert result["source_currentness_verified"] is False
