"""Exercise publication-time evidence checks against a synthetic approved registry."""

from dataclasses import replace
from datetime import date

import pytest

from app.agent.answer_evidence import AnswerEvidenceScope
from app.agent.catalogue_evidence import catalogue_passage
from app.agent.checkpoints import CheckpointState
from app.agent.contract import AnswerResult, EvidenceLinkedClaim, NextAction, OfficialChannel
from app.agent.run_events import read_run_events
from app.agent.worker import run_worker_step
from app.knowledge.review_service import revoke_version
from app.knowledge.search import resolve_approved_passage
from app.knowledge.service_areas import CaseLocation, EffectivePeriod
from test_agent_run_events import queued_run  # noqa: F401 - shared synthetic run fixture
from test_knowledge_search import OTHER_HTML, SCOPE, _approve, _create, _search
from test_service_areas import area


@pytest.fixture
def approved_citation(client, auth_headers):
    version, digest = _create(client)
    _approve(client, version, digest)
    [found] = _search(client, auth_headers("alice"), limit=1).json()["evidence"]
    with client.app.state.session_factory() as db:
        passage = resolve_approved_passage(db, citation_id=found["citation_id"], **SCOPE)
        assert passage is not None
        return catalogue_passage(passage).citation, digest


@pytest.fixture
def proposal(approved_citation):
    citation, _ = approved_citation
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
    )
    answer = AnswerResult(
        explanation="Synthetic official source statement.",
        verification_status="verified",
        official_channel=OfficialChannel(label="Synthetic contact", url=citation.official_url),
        next_action=NextAction(label="Open contact", operation="open_official_channel"),
        citations=[citation],
        claims=[EvidenceLinkedClaim(kind="channel", statement="Synthetic contact", evidence_ids=[citation.passage_id])],
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
    assert _finish(queued_run, answer, scope) == answer


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
