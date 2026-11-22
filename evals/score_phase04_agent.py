"""Score isolated agent components on the Phase 4 synthetic development set."""

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agent.answer_evidence import (
    AnswerEvidenceScope,
    ClaimPassageSupport,
    ReviewedClaimSupport,
    revalidate_answer_evidence,
)
from app.agent.candidate_resolution import choose_candidate_step
from app.agent.catalogue_evidence import catalogue_passage
from app.agent.checkpoints import CheckpointState
from app.agent.contract import (
    AnswerResult, Citation, ClarifyingQuestion, EvidenceLinkedClaim, MessageGoal, SendMessage,
)
from app.agent.intent_extraction import extract_intent
from app.agent.run_requests import StoredMessage, accept_message
from app.agent.threads import create_thread, link_case_to_thread
from app.agent.tool_access import ToolAccessDenied
from app.agent.tool_contract import parse_tool_call
from app.agent.tool_execution import ToolCapabilityUnavailable, check_tool_execution
from app.agent.worker import RequestClarification, run_worker_step
from app.auth.tokens import Principal
from app.cases.model import CaseRecord
from app.database import Base
from app.knowledge.entity_matching import CatalogueName
from app.knowledge.model import KnowledgeSource
from app.knowledge.review_service import approve_version, revoke_version
from app.knowledge.search import search_approved_passages
from app.knowledge.service_areas import CaseLocation, ServiceArea
from app.knowledge.snapshots import ingest_snapshot
from app.rules.engine import JURISDICTION, PROCEDURE


DATASET = Path(__file__).with_name("fixtures") / "phase04_agent_development.json"
ALIASES = {
    # The Phase 2 synthetic example pairs the explicit registration phrase with
    # the residence-change task. A generic address remains outside this alias.
    PROCEDURE: (
        "cambio di residenza", "registered address", "address change", "change of registered residence",
        "indirizzo all’anagrafe", "file the residence change", "file my residence change",
        "register a new address", "register my new address",
        "comunicare il nuovo indirizzo", "registrare il nuovo indirizzo",
    ),
    "marriage_banns": ("pubblicazioni di matrimonio", "marriage banns"),
    "residence_permit_renewal": ("permesso di soggiorno", "residence permit"),
}
PLACES = {"milano": JURISDICTION, "torino": "IT-TO-TORINO"}
NAMES = tuple(
    CatalogueName(key, "procedure", names[0], name, "reviewed_alias", "synthetic-eval-alias", approved_for_search=True)
    for key, names in ALIASES.items() for name in names
) + tuple(
    CatalogueName(place, "municipality", name, name, "reviewed_alias", "synthetic-eval-alias", approved_for_search=True)
    for name, place in {"Milano": JURISDICTION, "Milan": JURISDICTION, "Torino": PLACES["torino"]}.items()
)
DIMENSIONS = ("intent", "procedure_retrieval", "evidence", "question_quality", "tool_authorization")
SYNTHETIC_REVIEWER = "phase04-offline-fixture"


@dataclass(frozen=True)
class EvidenceFixture:
    reference: str
    pinned_passage: str
    citation: Citation
    assignment: ServiceArea
    text: str
    digest: str


def _evidence_fixtures(db, data):
    fixtures = []
    for reference, record in data["references"].items():
        signed = record.get("signed_evidence")
        if signed is None:
            continue
        for index, pinned in enumerate(signed["passage_ids"]):
            source_id = f"synthetic-{reference}-{index}"
            statement = f"Passaggio sintetico per la verifica locale numero {len(fixtures) + 1}."
            source = KnowledgeSource(
                id=source_id, institution="Synthetic evaluation registry", title="Synthetic evaluation",
                official_url=f"https://www.comune.milano.it/synthetic-phase04/{source_id}",
                jurisdiction=record["jurisdiction"], procedure_id=record["procedure_id"], language="it",
                document_type="service_page", status="candidate",
            )
            db.add(source)
            db.flush()
            version = ingest_snapshot(db, source, f"<html><body><p>{statement}</p></body></html>".encode())
            approve_version(
                db, version_id=version.version_id, expected_digest=version.sha256,
                actor_subject=SYNTHETIC_REVIEWER, reason="Disposable evaluation fixture",
            )
            [passage] = search_approved_passages(
                db, jurisdiction=source.jurisdiction, procedure_id=source.procedure_id,
                language="it", query=f"numero {len(fixtures) + 1}",
            )
            citation = catalogue_passage(passage).citation
            assignment = ServiceArea(
                assignment_id=source_id, authority_id="synthetic-registry", procedure_id=source.procedure_id,
                case_location_role="destination", unit_type="municipality", unit_ids=(source.jurisdiction,),
                evidence_ref=citation.passage_id, approved_for_routing=True,
            )
            fixtures.append(EvidenceFixture(reference, pinned, citation, assignment, statement, version.sha256))
    return fixtures


def _locations(facts):
    municipality = facts.get("destination_municipality")
    if municipality is None:
        return {}
    return {"destination": CaseLocation(municipality_id=PLACES[municipality], confirmed=True)}


def _question_fields(message, case, facts, evidence):
    intent, procedures = case["opening_intent"], case["opening_procedure_ids"]
    # Supply gold intent and candidates to isolate question selection from classification errors.
    goals = []
    if intent == "plan_multiple_tasks":
        goals = [MessageGoal(procedure_candidates=[procedure]) for procedure in procedures]
        procedures = []
    state = CheckpointState(
        next_node="choose_next_step", intent=intent, procedure_candidates=procedures, goals=goals,
    )
    decision = choose_candidate_step(
        message, state, case_locations=_locations(facts), confirmed_dates={}, confirmed_circumstances={},
        assignments=tuple(item.assignment for item in evidence),
        trusted_passage_ids=frozenset(item.citation.passage_id for item in evidence),
        reviewed_labels={key: names[0] for key, names in ALIASES.items()}, catalogue_names=NAMES,
    )
    fields = decision.question.missing_fields if isinstance(decision, RequestClarification) else []
    return sorted("destination_municipality" if field == "destination" else field for field in fields)


def _publication(db, evidence, facts, language, *, claim_kind):
    citations = [item.citation for item in evidence]
    statement = "Synthetic notice, for the evaluation scope only."
    # Treat this claim as dependent on all of its references. A withdrawn passage breaks the whole claim.
    links = tuple(
        ClaimPassageSupport(item.citation.passage_id, item.assignment.assignment_id, item.text)
        for item in evidence
    )
    reviewed = ReviewedClaimSupport(kind="authority", language=language, statement=statement, passages=links)
    claim = EvidenceLinkedClaim(kind=claim_kind, statement=statement, evidence_ids=[c.passage_id for c in citations])
    draft = AnswerResult(explanation=statement, verification_status="verified", citations=citations, claims=[claim])
    scope = AnswerEvidenceScope(
        procedure_id=PROCEDURE, case_locations=_locations(facts), confirmed_dates={}, confirmed_circumstances={},
        assignments=tuple(item.assignment for item in evidence), claim_reviews=(reviewed,),
    )
    answer = revalidate_answer_evidence(db, draft, scope=scope, language=language)
    emitted = {citation.passage_id for citation in answer.citations}
    return sorted(item.pinned_passage for item in evidence if item.citation.passage_id in emitted)


def _tool_checks(factory):
    owner, other = Principal("evaluation-owner"), Principal("evaluation-other")
    case, sibling = uuid4(), uuid4()
    key = bytes(range(32))
    with factory.begin() as db:
        db.add_all(CaseRecord(id=str(case_id), owner_subject=owner.subject) for case_id in (case, sibling))
        db.flush()
        thread = create_thread(db, principal=owner)
        for case_id in (case, sibling):
            link_case_to_thread(db, thread_id=thread, case_id=case_id, principal=owner)
        accepted = accept_message(db, thread_id=thread, principal=owner, key=key, message=SendMessage(
            client_message_id=uuid4(), case_id=case, text="Synthetic case", language="en",
        ))
    context = {"thread_id": thread, "run_id": accepted.run_id, "principal": owner, "key": key}

    def probe(payload, actor):
        try:
            call = parse_tool_call(payload, catalogue_scopes={(PROCEDURE, JURISDICTION)})
        except (ValidationError, ValueError):
            return "invalid_scope_or_payload"
        try:
            with factory.begin() as db:
                check_tool_execution(db, **(context | {"principal": actor}), call=call)
        except ToolCapabilityUnavailable:
            return "capability_unavailable"
        except ToolAccessDenied:
            return "denied"
        return "allowed"

    read = {"tool": "read_case_context", "case_id": case}
    yield "queued_read", "denied", probe(read, owner)
    run_worker_step(factory, **context, execute=lambda *_: CheckpointState(next_node="choose_next_step"))
    evidence = {"tool": "find_evidence", "case_id": case, "query": "residenza",
                "scope": {"procedure_id": PROCEDURE, "location_id": JURISDICTION}}
    document = {"tool": "read_document_evidence", "case_id": case, "document_id": uuid4(), "field_ids": ["move_in_date"]}
    write = {"tool": "apply_approved_update", "case_id": case, "proposal_id": uuid4(),
             "client_operation_id": uuid4(), "expected_case_revision": 1}
    probes = (
        ("owned_running_read", "allowed", read, owner),
        ("owned_running_evidence", "allowed", evidence, owner),
        ("linked_sibling_read", "denied", read | {"case_id": sibling}, owner),
        ("foreign_principal_read", "denied", read, other),
        ("unreviewed_catalogue_scope", "invalid_scope_or_payload", evidence | {
            "scope": {"procedure_id": PROCEDURE, "location_id": PLACES["torino"]},
        }, owner),
        ("document_capability", "capability_unavailable", document, owner),
        ("write_without_approval", "denied", write, owner),
    )
    for probe_id, expected, payload, actor in probes:
        yield probe_id, expected, probe(payload, actor)
    question = ClarifyingQuestion(
        question_id=uuid4(), text="Which destination?", answer_shape="free_text", missing_fields=["destination"],
    )
    run_worker_step(factory, **context, execute=lambda _, state: RequestClarification(question, state))
    yield "paused_read", "denied", probe(read, owner)


def _score_cases(factory, data, evidence, record):
    for case in data["cases"]:
        for language in data["languages"]:
            opening = case["steps"][0]
            message = StoredMessage(opening["text"][language], language, None)
            extraction = extract_intent(message, catalogue_names=NAMES)
            case_key = f"{case['id']}:{language}"
            procedures = {item for goal in extraction.goals for item in goal.procedure_candidates}
            procedures.update(extraction.procedure_candidates)
            record("intent", case_key, case["opening_intent"], extraction.intent)
            record("procedure_retrieval", case_key, sorted(case["opening_procedure_ids"]), sorted(procedures))
            facts = dict(data["profiles"].get(case.get("initial_profile"), {}))
            facts.update(case.get("initial_facts", {}))
            facts.update(opening.get("facts", {}))
            if opening["expect"]["outcome"] in {"clarification", "choose_goal", "verified_guidance"}:
                record("question_quality", case_key, sorted(opening["expect"].get("fields", [])),
                       _question_fields(message, case, facts, evidence))

            # Roll back scenario mutations so that language twins and later cases start with identical evidence.
            with factory() as db:
                for step in case["steps"]:
                    facts.update(step.get("facts", {}))
                    expected = step["expect"]
                    if revoked := step.get("withdrawn_ref"):
                        for item in evidence:
                            if item.reference == revoked:
                                revoke_version(
                                    db, version_id=str(item.citation.source_version_id), expected_digest=item.digest,
                                    actor_subject=SYNTHETIC_REVIEWER, reason="Disposable source withdrawal",
                                )
                    if not case.get("initial_profile"):
                        continue
                    if expected["outcome"] not in {"verified_guidance", "source_gap", "clarification", "restore_question"}:
                        continue
                    claim_kind = "form_version" if "obsolete_form" in case["tags"] else "authority"
                    observed = _publication(db, evidence, facts, language, claim_kind=claim_kind)
                    pinned = sorted(
                        passage
                        for reference in expected.get("citation_refs", [])
                        for passage in data["references"][reference]["signed_evidence"]["passage_ids"]
                    )
                    record("evidence", f"{case_key}:{step['id']}", pinned, observed)


def run():
    raw = DATASET.read_bytes()
    data = json.loads(raw)
    rows = {dimension: [] for dimension in DIMENSIONS}

    def record(dimension, probe_id, expected, observed):
        rows[dimension].append({"id": probe_id, "expected": expected, "observed": observed,
                                "passed": expected == observed})

    engine = create_engine("sqlite+pysqlite:///:memory:")
    try:
        Base.metadata.create_all(engine)
        factory = sessionmaker(bind=engine)
        with factory.begin() as db:
            evidence = _evidence_fixtures(db, data)
        _score_cases(factory, data, evidence, record)
        for probe_id, expected, observed in _tool_checks(factory):
            record("tool_authorization", probe_id, expected, observed)
    finally:
        engine.dispose()

    metrics = {}
    for dimension, results in rows.items():
        passed = sum(row["passed"] for row in results)
        metrics[dimension] = {"passed": passed, "total": len(results),
                              "pass_rate": round(passed / len(results), 4), "rows": results}
    return {"dataset_id": data["dataset_id"], "dataset_sha256": sha256(raw).hexdigest(),
            "mode": "offline_synthetic_component_evaluation", "metrics": metrics}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(run(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
