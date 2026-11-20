"""Keep unresolved procedure context separate from verified route selection."""

import pytest

from app.agent.candidate_resolution import choose_candidate_step
from app.agent.checkpoints import CheckpointState
from app.agent.intent_extraction import identify_intent_step
from app.agent.run_requests import StoredMessage
from app.agent.worker import RequestClarification
from app.knowledge.entity_matching import CatalogueName


NAMES = tuple(CatalogueName(
    identifier, kind, name, name, "reviewed_alias", "synthetic-review", approved_for_search=True,
) for identifier, kind, name in (
    ("marriage_banns", "procedure", "marriage banns"),
    ("marriage_banns", "procedure", "pubblicazioni di matrimonio"),
    ("residence_permit_renewal", "procedure", "residence permit"),
    ("residence_permit_renewal", "procedure", "permesso di soggiorno"),
    ("torino", "municipality", "Torino"),
    ("asti", "municipality", "Asti"),
))


def _decide(text, language, *, names=NAMES):
    message = StoredMessage(text, language, None)
    state = identify_intent_step(message, CheckpointState(next_node="identify_intent"), catalogue_names=names)
    assert state.next_node == "choose_next_step"
    return choose_candidate_step(
        message, state, case_locations={}, confirmed_dates={}, confirmed_circumstances={},
        assignments=(), trusted_passage_ids=frozenset(), reviewed_labels={}, catalogue_names=names,
    )


@pytest.mark.parametrize(("text", "language", "fields"), [
    ("We reside in Torino. Where do we request our marriage banns?", "en", ["celebration_municipality"]),
    ("Ci sposiamo ad Asti. Come richiedo le pubblicazioni di matrimonio?", "it", ["residence_municipality"]),
    ("We live in Torino. We live in Asti. Where do we request marriage banns?", "en",
     ["residence_municipality", "celebration_municipality"]),
    ("We need marriage banns in Torino. Where do we start?", "en",
     ["residence_municipality", "celebration_municipality"]),
    ("Where should I renew my residence permit?", "en", ["permit_category"]),
    ("Come faccio a rinnovare il mio permesso di soggiorno?", "it", ["permit_category"]),
])
def test_asks_only_for_unresolved_procedure_details(text, language, fields):
    result = _decide(text, language)
    assert isinstance(result, RequestClarification)
    assert result.question.missing_fields == fields


@pytest.mark.parametrize(("text", "language"), [
    ("My letter tells me to renew by mail. Can I take the envelope to Questura?", "en"),
    ("La lettera indica di rinnovare per posta. Posso portare la busta alla Questura?", "it"),
])
def test_conflicting_user_reported_instructions_leave_filing_channel_unverified(text, language):
    result = _decide(text, language)
    assert result.next_action.operation == "verify_filing_channel"
    assert result.verification_status == "insufficient_evidence"
    assert not result.citations and result.official_channel is None


def test_banns_shorthand_does_not_create_a_procedure_without_a_reviewed_catalogue_name():
    result = _decide("We live in Torino and are getting married. Where should we publish the banns?", "en", names=())
    assert result.question.missing_fields == ["procedure"]


def test_first_application_is_not_asked_for_a_renewal_category():
    result = _decide("How do I apply for my first residence permit?", "en")
    assert not isinstance(result, RequestClarification)
    assert result.official_channel is None
