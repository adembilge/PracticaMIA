"""No real municipal or user approval is simulated by these signature tests."""
from copy import deepcopy

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.rules.approval import has_valid_human_review_signature
from app.rules.offline_sign import check_signable_catalog, sign_reviewed_catalog


def structural_fixture():
    return {
        "version": "TEST_FIXTURE_ONLY_1",
        "status": "active",
        "jurisdiction": "IT-MI-MILANO",
        "procedure_id": "milan_residence_change",
        "approved_by": "fixture-reviewer-not-a-human-approval",
        "approved_at": "2026-11-07T13:00:00Z",
        "complete_scenario_coverage": True,
        "rules": [
            {
                "id": "synthetic_route", "kind": "route", "status": "active",
                "condition": {
                    "field": "synthetic_eligibility", "operator": "equals",
                    "value": "yes",
                },
                "result": {"route": "supported_individual"},
                "evidence_refs": ["fictional-reference-only"],
            }
        ],
    }


def test_offline_signer_verifies_and_cannot_silently_expand_catalog():
    c = structural_fixture()
    # The signing helper does not provide legal or source approval.
    signed, pub = sign_reviewed_catalog(c, Ed25519PrivateKey.generate())
    assert has_valid_human_review_signature(signed, pub)
    assert signed["rules"] == c["rules"]
    signed["rules"][0]["evidence_refs"] = ["modified"]
    assert not has_valid_human_review_signature(signed, pub)
    assert "review_signature" not in c


@pytest.mark.parametrize("change", [
    {"status": "pending_review"},
    {"complete_scenario_coverage": False},
    {"approved_by": None},
    {"approved_at": "2026-11-07"},
    {"jurisdiction": "IT-MI-OTHER"},
    {"rules": []},
])
def test_signing_rejects_incomplete_invalid_or_pending_catalog(change):
    c = {**structural_fixture(), **change}
    with pytest.raises(ValueError):
        check_signable_catalog(c)


def test_signing_rejects_draft_metadata_or_unapproved_candidate_contract():
    c = structural_fixture()
    c["proposal_only"] = True
    with pytest.raises(ValueError):
        sign_reviewed_catalog(c, Ed25519PrivateKey.generate())
    c = structural_fixture()
    c["review_blockers"] = []
    with pytest.raises(ValueError):
        check_signable_catalog(c)


def test_signing_refuses_non_ed25519_input():
    with pytest.raises(TypeError):
        sign_reviewed_catalog(structural_fixture(), "not a signing key")
