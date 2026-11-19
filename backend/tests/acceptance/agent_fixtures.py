"""Real Phase 4 persistence with a deterministic, disposable conversation."""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from secrets import token_bytes
from threading import Event, Thread
from uuid import uuid4

from app.agent.answer_evidence import AnswerEvidenceScope, ClaimPassageSupport, ReviewedClaimSupport
from app.agent.approval_resume import ApprovedCaseUpdates
from app.agent.candidate_resolution import choose_candidate_step
from app.agent.catalogue_evidence import catalogue_passage
from app.agent.checkpoints import CheckpointState
from app.agent.contract import (
    AnswerResult, ApprovalProposal, ClarifyingQuestion, EvidenceLinkedClaim, OfficialChannel, SendMessage,
)
from app.agent.intent_extraction import identify_intent_step
from app.agent.reconnect_router import build_reconnect_router
from app.agent.run_requests import accept_message
from app.agent.threads import create_thread, link_case_to_thread
from app.agent.worker import RequestApproval, RequestClarification, run_worker_batch, run_worker_step
from app.auth.tokens import Principal
from app.cases.intake_model import CaseIntake
from app.cases.model import CaseRecord
from app.knowledge.entity_matching import CatalogueName
from app.knowledge.model import KnowledgeSource
from app.knowledge.review_service import approve_version
from app.knowledge.search import search_approved_passages
from app.knowledge.service_areas import CaseLocation, ServiceArea
from app.knowledge.snapshots import ingest_snapshot


SOURCE_TEXT = "Questo esempio sintetico riguarda il cambio di residenza."
SOURCE_SCOPE = {"jurisdiction": "IT-MI-MILANO", "procedure_id": "milan_residence_change", "language": "it"}
GOAL_NAMES = tuple(
    CatalogueName(id_, entity, label, label, "reviewed_alias", "synthetic-goal-review", approved_for_search=True)
    for id_, entity, label in (
        ("fixture-address", "procedure", "Synthetic address change"),
        ("fixture-tax", "procedure", "Synthetic tax update"),
        ("fixture-milan", "municipality", "Milan"),
        ("fixture-como", "municipality", "Como"),
    )
)


class AgentReconnectFixture:
    def __init__(self, api):
        self.sessions = api.state.session_factory
        self.key = token_bytes(32)
        self.citation, self.claim, self.channel, self.evidence_scope = self.seed_source()
        self.seed_goal_choice()
        stop = self.seed_question("Which synthetic route should be stopped?")
        self.proposal_case_id = self.seed_proposal()
        api.include_router(build_reconnect_router(
            key=self.key, case_updates=ApprovedCaseUpdates(self.proposal_revision, self.write_proposal),
            read_evidence_scope=lambda *_: self.evidence_scope,
        ))
        self.replaced_question_id = self.seed_question("Which synthetic detail should both tabs see first?")
        self.followup_question = ClarifyingQuestion(
            question_id=uuid4(), text="Which synthetic detail should the refreshed tab see?",
            answer_shape="single_choice", options=["Fixture A", "Fixture B"], missing_fields=["housing_basis"],
        )
        topic = self.seed_question("Which synthetic detail should stay open when changing topics?")
        date = self.seed_question("What was the synthetic move-in date?", calendar_date=True)
        self.municipality_question_id = self.seed_question("Which synthetic municipality applies?")
        self.question_ids = {
            stop, topic, date, self.municipality_question_id, self.replaced_question_id, self.followup_question.question_id,
        }

    def seed_source(self):
        with self.sessions.begin() as db:
            source = KnowledgeSource(
                id="acceptance-agent-source", official_url="https://www.comune.milano.it/synthetic-acceptance-source",
                institution="Synthetic publisher", title="Synthetic residence source",
                status="candidate", document_type="service_page", **SOURCE_SCOPE,
            )
            db.add(source)
            db.flush()
            version = ingest_snapshot(
                db, source, f"<html><body><h1>Passaggio sintetico</h1><p>{SOURCE_TEXT}</p></body></html>".encode(),
            )
        with self.sessions.begin() as db:
            approve_version(
                db, version_id=version.version_id, expected_digest=version.sha256,
                actor_subject="synthetic-ci-reviewer", reason="Disposable source card fixture",
            )
            passage = next(
                row for row in search_approved_passages(db, query="esempio sintetico", **SOURCE_SCOPE)
                if row.source_id == "acceptance-agent-source"
            )
        citation = catalogue_passage(passage).citation
        channel = OfficialChannel(label="Synthetic residence service", url=citation.official_url)
        claim = EvidenceLinkedClaim(
            kind="channel", statement="The synthetic passage concerns a residence change channel.",
            evidence_ids=[citation.passage_id],
        )
        assignment = ServiceArea(
            assignment_id="synthetic-source-area", authority_id="synthetic-authority",
            procedure_id=citation.procedure_id, case_location_role="destination",
            unit_type="municipality", unit_ids=(citation.location_id,), evidence_ref=citation.passage_id,
            active=True, approved_for_routing=True,
        )
        scope = AnswerEvidenceScope(
            procedure_id=citation.procedure_id,
            case_locations={"destination": CaseLocation(municipality_id=citation.location_id, confirmed=True)},
            confirmed_dates={}, confirmed_circumstances={}, assignments=(assignment,),
            claim_reviews=(ReviewedClaimSupport(
                kind=claim.kind, language="en", statement=claim.statement,
                passages=(ClaimPassageSupport(citation.passage_id, assignment.assignment_id, SOURCE_TEXT),),
                official_channel=channel,
            ),),
        )
        return citation, claim, channel, scope

    def seed_proposal(self):
        principal = Principal("alice")
        case_id = uuid4()
        with self.sessions.begin() as db:
            db.add(CaseRecord(id=str(case_id), owner_subject=principal.subject))
            db.flush()
            db.add(CaseIntake(
                case_id=str(case_id), owner_subject=principal.subject, facts={"move_in_date": "2026-11-05"},
            ))
            thread_id = create_thread(db, principal=principal)
            if not link_case_to_thread(db, thread_id=thread_id, case_id=case_id, principal=principal):
                raise RuntimeError("Expected to link the synthetic proposal case")
            run = accept_message(
                db, thread_id=thread_id, principal=principal, key=self.key,
                message=SendMessage(
                    client_message_id=uuid4(), text="Synthetic move-in date proposal", language="en", case_id=case_id,
                ),
            )
        proposal = ApprovalProposal(
            proposal_id=uuid4(), case_id=case_id, field_id="move_in_date",
            previous_value="2026-11-05", proposed_value="2026-11-06",
            rationale="The user supplied a corrected move-in date.", expected_case_revision=7,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )
        snapshot = run_worker_step(
            self.sessions, thread_id=thread_id, run_id=run.run_id, principal=principal, key=self.key,
            execute=lambda *_: RequestApproval(proposal, CheckpointState(next_node="verify_and_respond")),
        )
        if snapshot.status != "waiting_for_approval" or snapshot.pending_proposal != proposal:
            raise RuntimeError("Expected the synthetic run to pause for proposal review")
        return case_id

    def proposal_revision(self, db, case_id):
        if case_id != self.proposal_case_id:
            return None
        intake = db.get(CaseIntake, str(case_id))
        return 7 if intake and intake.facts == {"move_in_date": "2026-11-05"} else None

    def write_proposal(self, db, proposal):
        if proposal.case_id != self.proposal_case_id or proposal.field_id != "move_in_date":
            raise RuntimeError("The synthetic writer only updates its fixture date")
        intake = db.get(CaseIntake, str(proposal.case_id))
        intake.facts = {"move_in_date": proposal.proposed_value}
        return proposal.expected_case_revision + 1

    def seed_question(self, prompt, *, calendar_date=False):
        principal = Principal("alice")
        with self.sessions.begin() as db:
            thread_id = create_thread(db, principal=principal)
            accepted = accept_message(
                db, thread_id=thread_id, principal=principal, key=self.key,
                message=SendMessage(client_message_id=uuid4(), text="Synthetic move", language="en"),
            )
        context = {"thread_id": thread_id, "run_id": accepted.run_id, "principal": principal, "key": self.key}
        question = ClarifyingQuestion(
            question_id=uuid4(), text=prompt,
            answer_shape="free_text" if calendar_date else "single_choice",
            options=[] if calendar_date else ["Fixture A", "Fixture B"],
            missing_fields=["move_in_date" if calendar_date else "jurisdiction"],
            answer_format="calendar_date" if calendar_date else None,
            reply_hint="Enter a valid move-in date in YYYY-MM-DD or DD/MM/YYYY format." if calendar_date else None,
        )
        snapshot = run_worker_step(self.sessions, **context, execute=lambda *_: RequestClarification(
            question, CheckpointState(next_node="find_evidence"),
        ))
        if snapshot.status != "waiting_for_information":
            raise RuntimeError("Expected the synthetic run to pause for a question")
        return question.question_id

    def seed_goal_choice(self):
        principal = Principal("alice")
        with self.sessions.begin() as db:
            thread_id = create_thread(db, principal=principal)
            accepted = accept_message(
                db, thread_id=thread_id, principal=principal, key=self.key,
                message=SendMessage(
                    client_message_id=uuid4(), language="en",
                    text="Synthetic address change in Milan; synthetic tax update in Como.",
                ),
            )
        context = {"thread_id": thread_id, "run_id": accepted.run_id, "principal": principal, "key": self.key}
        run_worker_step(self.sessions, **context, execute=lambda *_: CheckpointState(next_node="identify_intent"))
        run_worker_step(self.sessions, **context, execute=lambda message, state: identify_intent_step(
            message, state, catalogue_names=GOAL_NAMES,
        ))
        snapshot = run_worker_step(self.sessions, **context, execute=self.choose_goal)
        if snapshot.status != "waiting_for_information":
            raise RuntimeError("Expected a pending choice between the synthetic goals")

    def choose_goal(self, message, state):
        return choose_candidate_step(
            message, state, case_locations={}, confirmed_dates={}, confirmed_circumstances={},
            assignments=(), trusted_passage_ids=frozenset(),
            reviewed_labels={name.catalogue_id: name.display_name for name in GOAL_NAMES},
        )

    def finish(self, message, state):
        if state.goals:
            return self.choose_goal(message, state)
        if message.approval_applied is not None:
            if state.next_node != "verify_and_respond" or message.case_id != self.proposal_case_id:
                raise RuntimeError("The worker did not resume the saved proposal run")
            return AnswerResult(
                explanation="The approved move-in date was saved.", verification_status="insufficient_evidence",
            )
        if (
            state.next_node != "find_evidence" or message.clarification_reply is None
            or message.clarification_reply.question_id not in self.question_ids
        ):
            raise RuntimeError("The worker did not resume from the recorded answer")
        if message.clarification_reply.question_id == self.replaced_question_id:
            return RequestClarification(self.followup_question, state)
        with_source = message.clarification_reply.question_id == self.municipality_question_id
        return AnswerResult(
            explanation=f"Received {message.clarification_reply.text}.",
            verification_status="insufficient_evidence",
            citations=[self.citation] if with_source else [],
            claims=[self.claim] if with_source else [],
            official_channel=self.channel if with_source else None,
        )

    @contextmanager
    def poll_queue(self):
        stop = Event()

        def poll():
            while not stop.wait(0.1):
                run_worker_batch(
                    self.sessions, key=self.key, lease_for=timedelta(seconds=30),
                    execute=self.finish, max_steps=4,
                    read_evidence_scope=lambda *_: self.evidence_scope,
                )

        worker = Thread(target=poll, name="acceptance-agent-worker", daemon=True)
        worker.start()
        try:
            yield
        finally:
            stop.set()
            worker.join()
