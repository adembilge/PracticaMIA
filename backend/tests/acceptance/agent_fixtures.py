"""Real Phase 4 persistence with a deterministic, disposable conversation."""

from contextlib import contextmanager
from datetime import timedelta
from secrets import token_bytes
from threading import Event, Thread
from uuid import uuid4

from app.agent.checkpoints import CheckpointState
from app.agent.contract import AnswerResult, ClarifyingQuestion, SendMessage
from app.agent.reconnect_router import build_reconnect_router
from app.agent.run_requests import accept_message
from app.agent.threads import create_thread
from app.agent.worker import RequestClarification, run_worker_batch, run_worker_step
from app.auth.tokens import Principal


class AgentReconnectFixture:
    def __init__(self, api):
        self.sessions = api.state.session_factory
        self.key = token_bytes(32)
        api.include_router(build_reconnect_router(key=self.key))
        stop = self.seed_question("Which synthetic route should be stopped?")
        topic = self.seed_question("Which synthetic detail should stay open when changing topics?")
        date = self.seed_question("What was the synthetic move-in date?", calendar_date=True)
        municipality = self.seed_question("Which synthetic municipality applies?")
        self.question_ids = {stop, topic, date, municipality}

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
        return AnswerResult(
            explanation=f"Received {message.clarification_reply.text}.",
            verification_status="insufficient_evidence",
        )

    @contextmanager
    def poll_queue(self):
        stop = Event()

        def poll():
            while not stop.wait(0.1):
                run_worker_batch(
                    self.sessions, key=self.key, lease_for=timedelta(seconds=30),
                    execute=self.finish, max_steps=4,
                )

        worker = Thread(target=poll, name="acceptance-agent-worker", daemon=True)
        worker.start()
        try:
            yield
        finally:
            stop.set()
            worker.join()
