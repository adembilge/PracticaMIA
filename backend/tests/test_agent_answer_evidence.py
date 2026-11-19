"""Exercise publication-time evidence checks against a synthetic approved registry."""

from dataclasses import replace
from datetime import date

import pytest

from app.agent.answer_evidence import AnswerEvidenceScope, ClaimPassageSupport, ReviewedClaimSupport
from app.agent.catalogue_evidence import catalogue_passage
from app.agent.checkpoints import CheckpointState
from app.agent.contract import AnswerResult, EvidenceLinkedClaim, NextAction, OfficialChannel
from app.agent.run_events import read_run_events
from app.agent.worker import run_worker_step
from app.knowledge.review_service import revoke_version
from app.knowledge.search import resolve_approved_passage
from app.knowledge.service_areas import CaseLocation, EffectivePeriod
from test_agent_run_events import queued_run  # noqa: F401 - shared synthetic run fixture
from test_knowledge_search import HTML, OTHER_HTML, SCOPE, _approve, _create, _search
from test_service_areas import area


CONTACT_QUOTE = "Lo sportello di esempio offre assistenza per questa procedura simulata."
DEADLINE_QUOTE = "La scadenza simulata cade il 30 aprile per le domande in locazione."
REVIEW_HTML = HTML.replace(
    b"</p><h2>Contratto", f" {CONTACT_QUOTE}</p><h2>Contratto".encode(),
).replace(b"</body>", f"<h2>Termini</h2><p>{DEADLINE_QUOTE}</p></body>".encode())


def _citation_for(client, auth_headers, query):
    [found] = _search(client, auth_headers("alice"), query=query, limit=1).json()["evidence"]
    with client.app.state.session_factory() as db:
        passage = resolve_approved_passage(db, citation_id=found["citation_id"], **SCOPE)
        assert passage is not None
        return catalogue_passage(passage).citation


@pytest.fixture
def approved_citation(client, auth_headers):
    version, digest = _create(client, html=REVIEW_HTML)
    _approve(client, version, digest)
    return _citation_for(client, auth_headers, "residenza"), digest


@pytest.fixture
def proposal(approved_citation):
    citation, _ = approved_citation
    channel = OfficialChannel(label="Synthetic contact", url=citation.official_url)
    claim = EvidenceLinkedClaim(
        kind="channel", statement="Lo sportello offre assistenza per la pratica simulata.",
        evidence_ids=[citation.passage_id],
    )
    assignment = replace(
        area(
            procedure_id=citation.procedure_id, evidence_ref=citation.passage_id,
            unit_ids=(citation.location_id, "other-municipality"),
        ),
        effective_period=EffectivePeriod("filing_date", date(2026, 4, 1), date(2026, 4, 30)),
        required_circumstances=(("housing_basis", "rental"),),
    )
    scope = AnswerEvidenceScope(
        procedure_id=citation.procedure_id,
        case_locations={"destination": CaseLocation(municipality_id=citation.location_id, confirmed=True)},
        confirmed_dates={"filing_date": date(2026, 4, 30)},
        confirmed_circumstances={"housing_basis": "rental"},
        assignments=(assignment,),
        claim_reviews=(ReviewedClaimSupport(
            kind=claim.kind, language="it", statement=claim.statement, official_channel=channel,
            passages=(ClaimPassageSupport(citation.passage_id, assignment.assignment_id, CONTACT_QUOTE),),
        ),),
    )
    answer = AnswerResult(
        explanation="Synthetic official source statement. There is a 99 euro fee.",
        verification_status="verified",
        official_channel=channel,
        next_action=NextAction(label="Pay the 99 euro fee", operation="open_official_channel"),
        citations=[citation],
        claims=[claim],
    )
    return answer, scope


def _finish(queued_run, answer, scope):
    factory, context, _, _ = queued_run

    def read_scope(db, thread_id, run_id, case_id, principal):
        assert db.in_transaction()
        assert (thread_id, run_id, case_id, principal) == (
            context["thread_id"], context["run_id"], None, context["principal"],
        )
        return scope

    worker = {"read_evidence_scope": read_scope} if scope else {}
    snapshot = run_worker_step(factory, **context, execute=lambda *_: answer, **worker)
    assert snapshot.status == "completed"
    with factory() as db:
        [terminal] = read_run_events(db, **context, after_seq=snapshot.last_event_seq - 1).events
        assert terminal.result == snapshot.result
    return snapshot.result


def _assert_withheld(result):
    assert result.verification_status == "insufficient_evidence"
    assert "Synthetic official source statement" not in result.explanation
    assert result.next_action.operation == "provide_information"
    assert result.official_channel is None
    assert result.claims == result.citations == []


def test_active_matching_passage_is_revalidated_without_prior_checkpoint_retrieval(queued_run, proposal):
    answer, scope = proposal
    assert _finish(queued_run, answer, scope) == answer.model_copy(update={
        "explanation": answer.claims[0].statement,
        "next_action": NextAction(label="Apri il canale ufficiale", operation="open_official_channel"),
    })


def test_valid_authority_page_does_not_prove_an_absent_deadline(queued_run, proposal):
    answer, scope = proposal
    claim = EvidenceLinkedClaim(
        kind="deadline", statement="La scadenza simulata cade il 30 aprile.",
        evidence_ids=[answer.citations[0].passage_id],
    )
    review = replace(
        scope.claim_reviews[0], kind=claim.kind, statement=claim.statement, official_channel=None,
        passages=(replace(scope.claim_reviews[0].passages[0], quote=DEADLINE_QUOTE),),
    )
    answer = answer.model_copy(update={"claims": [claim], "official_channel": None, "next_action": None})
    result = _finish(queued_run, answer, replace(scope, claim_reviews=(review,)))
    _assert_withheld(result)
    assert "30 aprile" not in result.explanation


@pytest.mark.parametrize("missing_information", [[], ["filing_date"]])
def test_a_supported_channel_survives_an_unreviewed_fee_claim(queued_run, proposal, missing_information):
    answer, scope = proposal
    fee = EvidenceLinkedClaim(kind="fee", statement="Costo: 99 euro.", evidence_ids=answer.claims[0].evidence_ids)
    result = _finish(queued_run, answer.model_copy(update={
        "claims": [*answer.claims, fee], "missing_information": missing_information,
    }), scope)
    assert result.verification_status == "insufficient_evidence"
    assert result.claims == answer.claims
    assert result.citations == answer.citations
    assert result.official_channel == answer.official_channel
    assert result.missing_information == missing_information
    assert result.next_action.operation == ("provide_information" if missing_information else "open_official_channel")
    assert "99 euro" not in result.explanation
    assert "99 euro" not in result.next_action.label


def test_partial_answer_recovers_the_reviewed_channel_instead_of_a_proposed_unverified_url(queued_run, proposal):
    answer, scope = proposal
    alternative = OfficialChannel(label=answer.official_channel.label, url="https://example.invalid/")
    result = _finish(queued_run, answer.model_copy(update={"official_channel": alternative}), scope)
    assert result.verification_status == "insufficient_evidence"
    assert result.official_channel == answer.official_channel
    assert result.claims == answer.claims
    assert result.citations == answer.citations


def test_channel_claim_can_be_narrowed_to_its_independently_reviewed_statement(queued_run, proposal):
    answer, scope = proposal
    review = replace(scope.claim_reviews[0], statement=CONTACT_QUOTE)
    result = _finish(queued_run, answer, replace(scope, claim_reviews=(review,)))
    assert result.verification_status == "insufficient_evidence"
    assert [claim.statement for claim in result.claims] == [CONTACT_QUOTE]
    assert result.official_channel == answer.official_channel
    assert answer.claims[0].statement not in result.explanation


@pytest.mark.parametrize("change", [
    "unreviewed", "different-claim-type", "unreviewed-language", "different-scope", "blank-quote",
])
def test_claim_support_must_match_review_and_scope(queued_run, proposal, change):
    answer, scope = proposal
    review = scope.claim_reviews[0]
    if change == "unreviewed":
        scope = replace(scope, claim_reviews=())
    else:
        link = review.passages[0]
        reviews = {
            "different-claim-type": replace(review, kind="authority"),
            "unreviewed-language": replace(review, language="en"),
            "different-scope": replace(review, passages=(replace(link, assignment_id="unavailable-assignment"),)),
            "blank-quote": replace(review, passages=(replace(link, quote="  "),)),
        }
        scope = replace(scope, claim_reviews=(reviews[change],))
    _assert_withheld(_finish(queued_run, answer, scope))


@pytest.mark.parametrize("assistance", ["valid", "expired", "ambiguous"])
def test_trusted_assistance_helps_verify_missing_information(client, auth_headers, queued_run, proposal, assistance):
    answer, scope = proposal
    original = answer.citations[0]
    deadline = _citation_for(client, auth_headers, "scadenza")
    deadline_assignment = replace(scope.assignments[0], assignment_id="deadline", evidence_ref=deadline.passage_id)
    unsupported_claim = EvidenceLinkedClaim(
        kind="deadline", statement="La scadenza è domani.", evidence_ids=[deadline.passage_id],
    )
    draft = answer.model_copy(update={
        "claims": [unsupported_claim], "citations": [deadline], "official_channel": None, "next_action": None,
    })
    scopes = {"assignments": (*scope.assignments, deadline_assignment), "assistance_citations": (original,)}
    if assistance == "expired":
        expired = replace(
            scope.assignments[0], effective_period=EffectivePeriod("filing_date", effective_until=date(2026, 4, 29)),
        )
        scopes["assignments"] = (expired, deadline_assignment)
    if assistance == "ambiguous":
        other = replace(scope.claim_reviews[0], official_channel=OfficialChannel(
            label="Second reviewed channel", url="https://example.invalid/synthetic-contact",
        ))
        scopes["claim_reviews"] = (*scope.claim_reviews, other)
    result = _finish(queued_run, draft, replace(scope, **scopes))
    if assistance == "valid":
        assert result.verification_status == "insufficient_evidence"
        assert result.claims == answer.claims
        assert result.citations == [original]
        assert result.official_channel == answer.official_channel
        assert result.next_action.operation == "open_official_channel"
        assert "domani" not in result.explanation
    else:
        _assert_withheld(result)


def test_revoked_source_only_removes_its_dependent_claims(client, auth_headers, queued_run, proposal):
    answer, scope = proposal
    deadline_html = (
        f"<html><body><h1>Termini</h1><p>Seconda fonte sintetica. {DEADLINE_QUOTE}</p></body></html>"
    ).encode()
    version, digest = _create(client, source_id="milano-residence-faq", html=deadline_html)
    _approve(client, version, digest)
    deadline = _citation_for(client, auth_headers, "seconda")
    assert deadline.source_id == "milano-residence-faq"
    expired_contact = answer.citations[0]
    deadline_assignment = replace(scope.assignments[0], assignment_id="deadline", evidence_ref=deadline.passage_id)
    deadline_claim = EvidenceLinkedClaim(
        kind="deadline", statement=DEADLINE_QUOTE, evidence_ids=[deadline.passage_id],
    )
    deadline_review = ReviewedClaimSupport(
        kind=deadline_claim.kind, language="it", statement=deadline_claim.statement,
        passages=(ClaimPassageSupport(deadline.passage_id, deadline_assignment.assignment_id, DEADLINE_QUOTE),),
    )
    scope = replace(
        scope, assignments=(*scope.assignments, deadline_assignment), claim_reviews=(*scope.claim_reviews, deadline_review),
    )
    with client.app.state.session_factory.begin() as db:
        source = resolve_approved_passage(db, citation_id=expired_contact.passage_id, **SCOPE)
        assert source is not None
        revoke_version(
            db, version_id=source.source_version_id, expected_digest=source.source_sha256,
            actor_subject="synthetic-reviewer", reason="Withdrawn test fixture",
        )
    result = _finish(queued_run, answer.model_copy(update={
        "claims": [*answer.claims, deadline_claim], "citations": [expired_contact, deadline],
    }), scope)
    assert result.verification_status == "insufficient_evidence"
    assert result.claims == [deadline_claim]
    assert result.citations == [deadline]
    assert result.official_channel is None
    assert result.next_action.operation == "provide_information"
    assert DEADLINE_QUOTE in result.explanation


@pytest.mark.parametrize("use_all_sources", [True, False])
def test_joint_support_requires_the_complete_reviewed_passage_set(
    client, auth_headers, queued_run, proposal, use_all_sources,
):
    answer, scope = proposal
    deadline_citation = _citation_for(client, auth_headers, "scadenza")
    assert deadline_citation.passage_id != answer.citations[0].passage_id
    deadline_assignment = replace(
        scope.assignments[0], assignment_id="deadline-assignment", evidence_ref=deadline_citation.passage_id,
    )
    claim = EvidenceLinkedClaim(
        kind="deadline", statement=DEADLINE_QUOTE,
        evidence_ids=[answer.citations[0].passage_id, deadline_citation.passage_id],
    )
    review = ReviewedClaimSupport(
        kind=claim.kind, language="it", statement=claim.statement,
        passages=(*scope.claim_reviews[0].passages, ClaimPassageSupport(
            deadline_citation.passage_id, deadline_assignment.assignment_id, DEADLINE_QUOTE,
        )),
    )
    scope = replace(scope, claim_reviews=(review,), assignments=(*scope.assignments, deadline_assignment))
    answer = answer.model_copy(update={
        "claims": [claim] if use_all_sources else [claim.model_copy(update={"evidence_ids": claim.evidence_ids[1:]})],
        "citations": [*answer.citations, deadline_citation] if use_all_sources else [deadline_citation],
        "official_channel": None, "next_action": None,
    })
    result = _finish(queued_run, answer, scope)
    if use_all_sources:
        assert result == answer.model_copy(update={"explanation": DEADLINE_QUOTE})
    else:
        _assert_withheld(result)


@pytest.mark.parametrize("scope_changes", [
    {"procedure_id": "another-procedure"},
    {"case_locations": {"destination": CaseLocation(municipality_id="other-municipality", confirmed=True)}},
    {"case_locations": {"destination": CaseLocation(municipality_id=SCOPE["jurisdiction"])}},
    {"confirmed_dates": {"filing_date": date(2026, 5, 1)}},
    {"confirmed_dates": {"move_in_date": date(2026, 4, 1)}},
    {"confirmed_circumstances": {"housing_basis": "owner"}},
    {"confirmed_circumstances": {}},
    {"assignments": ()},
])
def test_inapplicable_scope_withholds_cited_answer(queued_run, proposal, scope_changes):
    answer, scope = proposal
    _assert_withheld(_finish(queued_run, answer, replace(scope, **scope_changes)))


def test_unavailable_trusted_scope_withholds_cited_answer(queued_run, proposal):
    answer, _ = proposal
    _assert_withheld(_finish(queued_run, answer, None))


def test_altered_citation_metadata_withholds_official_channel(queued_run, proposal):
    answer, scope = proposal
    changed = answer.citations[0].model_copy(update={"publisher": "Unreviewed publisher"})
    answer = answer.model_copy(update={
        "verification_status": "insufficient_evidence", "citations": [changed],
        "missing_information": ["other_case_fact"],
    })
    result = _finish(queued_run, answer, scope)
    _assert_withheld(result)
    assert result.missing_information == ["other_case_fact"]


@pytest.mark.parametrize("change", ["revoke", "supersede"])
def test_stale_checkpoints_cannot_publish_withdrawn_or_replaced_passages(
    client, queued_run, approved_citation, proposal, change,
):
    factory, context, _, _ = queued_run
    answer, scope = proposal
    citation, digest = approved_citation
    state = CheckpointState(next_node="verify_and_respond", evidence_ids=[citation.passage_id])
    assert run_worker_step(factory, **context, execute=lambda *_: state).status == "running"
    if change == "revoke":
        with factory.begin() as db:
            revoke_version(
                db, version_id=str(citation.source_version_id), expected_digest=digest,
                actor_subject="synthetic-reviewer", reason="Withdrawn test fixture",
            )
    else:
        new_version, new_digest = _create(client, html=OTHER_HTML)
        _approve(client, new_version, new_digest)
    _assert_withheld(_finish(queued_run, answer, scope))
