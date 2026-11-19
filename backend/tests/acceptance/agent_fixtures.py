"""Real Phase 4 persistence with a deterministic, disposable conversation."""

from contextlib import contextmanager
from datetime import timedelta
from secrets import token_bytes
from threading import Event, Thread
from uuid import uuid4

from app.agent.answer_evidence import AnswerEvidenceScope, ClaimPassageSupport, ReviewedClaimSupport
from app.agent.catalogue_evidence import catalogue_passage
from app.agent.checkpoints import CheckpointState
from app.agent.contract import AnswerResult, ClarifyingQuestion, EvidenceLinkedClaim, SendMessage
from app.agent.reconnect_router import build_reconnect_router
from app.agent.run_requests import accept_message
from app.agent.threads import create_thread
from app.agent.worker import RequestClarification, run_worker_batch, run_worker_step
from app.auth.tokens import Principal
from app.knowledge.model import KnowledgeSource
from app.knowledge.review_service import approve_version
from app.knowledge.search import search_approved_passages
from app.knowledge.service_areas import CaseLocation, ServiceArea
from app.knowledge.snapshots import ingest_snapshot


SOURCE_TEXT = "Questo esempio sintetico riguarda il cambio di residenza."
SOURCE_SCOPE = {"jurisdiction": "IT-MI-MILANO", "procedure_id": "milan_residence_change", "language": "it"}


class AgentReconnectFixture:
    def __init__(self, api):
        self.sessions = api.state.session_factory
        self.key = token_bytes(32)
        api.include_router(build_reconnect_router(key=self.key))
        self.citation, self.claim, self.evidence_scope = self.seed_source()
        stop = self.seed_question("Which synthetic route should be stopped?")
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
        claim = EvidenceLinkedClaim(
            kind="condition", statement="The synthetic passage concerns a residence change.",
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
            ),),
        )
        return citation, claim, scope

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

    def finish(self, message, state):
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
