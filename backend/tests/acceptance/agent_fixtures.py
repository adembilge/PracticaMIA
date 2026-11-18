"""Real Phase 4 persistence with a deterministic, disposable conversation."""

from secrets import token_bytes
from uuid import uuid4

from app.agent.checkpoints import CheckpointState
from app.agent.contract import AnswerResult, ClarifyingQuestion, SendMessage
from app.agent.reconnect_router import build_reconnect_router
from app.agent.run_requests import accept_message
from app.agent.threads import create_thread
from app.agent.worker import RequestClarification, run_worker_step
from app.auth.tokens import Principal


class AgentReconnectFixture:
    def __init__(self, api):
        self.sessions = api.state.session_factory
        key = token_bytes(32)
        principal = Principal("alice")
        api.include_router(build_reconnect_router(key=key))
        with self.sessions.begin() as db:
            thread_id = create_thread(db, principal=principal)
            accepted = accept_message(
                db, thread_id=thread_id, principal=principal, key=key,
                message=SendMessage(client_message_id=uuid4(), text="Synthetic move", language="en"),
            )
        self.context = {"thread_id": thread_id, "run_id": accepted.run_id, "principal": principal, "key": key}
        self.question = ClarifyingQuestion(
            question_id=uuid4(), text="Which synthetic municipality applies?",
            answer_shape="single_choice", options=["Fixture A", "Fixture B"],
            missing_fields=["jurisdiction"],
        )
        snapshot = run_worker_step(self.sessions, **self.context, execute=lambda *_: RequestClarification(
            self.question, CheckpointState(next_node="find_evidence"),
        ))
        if snapshot.status != "waiting_for_information":
            raise RuntimeError("Expected the synthetic run to pause for a question")

    def advance(self) -> str:
        def finish(message, state):
            if (
                state.next_node != "find_evidence" or message.clarification_reply is None
                or message.clarification_reply.question_id != self.question.question_id
            ):
                raise RuntimeError("The worker did not resume from the recorded answer")
            return AnswerResult(
                explanation=f"Received {message.clarification_reply.text}.",
                verification_status="insufficient_evidence",
            )

        snapshot = run_worker_step(self.sessions, **self.context, execute=finish)
        return snapshot.status
