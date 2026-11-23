"""Authenticated Phase 4 transport, mounted only in isolated acceptance tests."""

from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import Field, model_validator
from sqlalchemy.orm import Session

from app.agent.answer_evidence import AnswerEvidenceScopeReader
from app.agent.approval_resume import ApprovedCaseUpdates, resume_approved_case_update
from app.agent.checkpoints import CheckpointConflict, RunRevisionConflict, stop_run, submit_clarification_reply
from app.agent.contract import (
    ActiveRunCursor, ActiveRunCursorTime, ActiveRunPage, ApprovalDecided, ClarificationReply, ContractModel,
    EventPage, Language, PassageId, PositiveInt, QuestionAnswered, RunSnapshot, SendMessage, StopRun,
    SubmitProposalDecision,
)
from app.agent.proposal_decisions import InvalidProposalValue, ProposalDecisionConflict, submit_proposal_decision
from app.agent.run_events import (
    ConversationBusy, EventConflict, InvalidClarificationReply, InvalidEventCursor, read_run_events, read_run_snapshot,
)
from app.agent.run_handoff import read_run_handoff
from app.agent.run_requests import (
    ConversationHistoryPage, _payload_cipher, accept_message, list_active_runs,
    list_recent_conversations, list_recent_runs, list_thread_history,
)
from app.agent.source_cards import RunSourceCard, read_run_source_card
from app.agent.threads import create_thread_for_message
from app.auth.tokens import Principal, get_principal
from app.database import get_session

AuthenticatedOwner = Annotated[Principal, Depends(get_principal)]
DatabaseSession = Annotated[Session, Depends(get_session)]
THREAD_PATH = "/threads/{thread_id}"
RUN_PATH = THREAD_PATH + "/runs/{run_id}"


ErrorCode = Literal[
    "unauthenticated", "unavailable", "invalid_request", "invalid_cursor", "invalid_reply",
    "stale_question", "stale_run", "stale_proposal", "invalid_proposal_value",
    "conversation_busy", "stale_thread", "message_conflict",
]


class ActiveRunsQuery(ContractModel):
    limit: int = Field(default=20, ge=1, le=50)
    before_accepted_at: ActiveRunCursorTime | None = None
    before_run_id: UUID | None = None

    @model_validator(mode="after")
    def validate_cursor(self):
        if (self.before_accepted_at is None) != (self.before_run_id is None):
            raise ValueError("Both active run cursor fields are required")
        return self


class AgentHttpError(ContractModel):
    code: ErrorCode
    message: str
    request_id: UUID


class CaseTaskMessage(SendMessage):
    case_id: UUID


class CaseTaskAccepted(ContractModel):
    run_id: UUID
    accepted_revision: PositiveInt


class FirstMessage(SendMessage):
    case_id: None = None
    expected_thread_revision: None = None


class ConversationAccepted(CaseTaskAccepted):
    thread_id: UUID


def _error(status: int, code: ErrorCode, message: str, *, headers=None) -> JSONResponse:
    error = AgentHttpError(code=code, message=message, request_id=uuid4())
    return JSONResponse(error.model_dump(mode="json"), status_code=status, headers=headers)


class _PrivateAgentRoute(APIRoute):
    def get_route_handler(self):
        handle = super().get_route_handler()

        async def private_response(request: Request):
            try:
                response = await handle(request)
            except RequestValidationError as exc:
                message = "Check the request parameters."
                if all(error["loc"] == ("body", "text") for error in exc.errors()):
                    message = "Enter a reply between 1 and 2,000 characters or select one of the offered choices."
                response = _error(422, "invalid_request", message)
            except InvalidEventCursor:
                response = _error(422, "invalid_cursor", "Use a cursor from this run.")
            except InvalidClarificationReply as exc:
                response = _error(422, "invalid_reply", str(exc))
            except InvalidProposalValue:
                response = _error(422, "invalid_proposal_value", "Enter a supported value for the proposed field.")
            except ProposalDecisionConflict:
                response = _error(409, "stale_proposal", "Review the current proposal before deciding.")
            except RunRevisionConflict:
                response = _error(409, "stale_run", "Reopen the run to check its current status.")
            except ConversationBusy:
                response = _error(409, "conversation_busy", "Wait for the current task to pause or finish, then try again.")
            except (CheckpointConflict, EventConflict):
                response = _error(409, "stale_question", "Reopen the run to check its current question.")
            except HTTPException as exc:
                if exc.status_code == 401:
                    response = _error(
                        401, "unauthenticated", "A valid bearer token is required.", headers=exc.headers,
                    )
                elif exc.status_code == 404:
                    response = _error(404, "unavailable", "Run unavailable.")
                else:
                    raise
            response.headers["Cache-Control"] = "private, no-store"
            return response

        return private_response


def build_reconnect_router(
    *, key: bytes, case_updates: ApprovedCaseUpdates | None = None,
    read_evidence_scope: AnswerEvidenceScopeReader | None = None,
) -> APIRouter:
    """Build the transport with a key supplied by the isolated application."""
    _payload_cipher(key)
    router = APIRouter(
        prefix="/api/v1/agent",
        route_class=_PrivateAgentRoute,
        responses={status: {"model": AgentHttpError} for status in (401, 404, 422)},
    )

    @router.get("/runs/active")
    def active_runs(
        query: Annotated[ActiveRunsQuery, Query()], principal: AuthenticatedOwner, db: DatabaseSession,
    ) -> ActiveRunPage:
        cursor = None
        if query.before_accepted_at is not None and query.before_run_id is not None:
            cursor = ActiveRunCursor(accepted_at=query.before_accepted_at, run_id=query.before_run_id)
        return list_active_runs(db, principal=principal, limit=query.limit, before=cursor)

    @router.get("/runs/recent")
    def recent_runs(
        query: Annotated[ActiveRunsQuery, Query()], principal: AuthenticatedOwner, db: DatabaseSession,
    ) -> ActiveRunPage:
        cursor = None
        if query.before_accepted_at is not None and query.before_run_id is not None:
            cursor = ActiveRunCursor(accepted_at=query.before_accepted_at, run_id=query.before_run_id)
        return list_recent_runs(db, principal=principal, limit=query.limit, before=cursor)

    @router.get("/conversations/recent")
    def recent_conversations(
        query: Annotated[ActiveRunsQuery, Query()], principal: AuthenticatedOwner, db: DatabaseSession,
    ) -> ActiveRunPage:
        cursor = None
        if query.before_accepted_at is not None and query.before_run_id is not None:
            cursor = ActiveRunCursor(accepted_at=query.before_accepted_at, run_id=query.before_run_id)
        return list_recent_conversations(db, principal=principal, limit=query.limit, before=cursor)

    @router.get(THREAD_PATH + "/history")
    def thread_history(
        thread_id: UUID, principal: AuthenticatedOwner, db: DatabaseSession,
        limit: Annotated[int, Query(ge=1, le=30)] = 20,
        before_revision: Annotated[int | None, Query(ge=1)] = None,
    ) -> ConversationHistoryPage:
        history = list_thread_history(
            db, thread_id=thread_id, principal=principal, key=key,
            limit=limit, before_revision=before_revision,
        )
        if history is None:
            raise HTTPException(404)
        return history

    @router.post("/conversations", status_code=202, responses={409: {"model": AgentHttpError}})
    def start_conversation(
        message: FirstMessage, principal: AuthenticatedOwner, db: DatabaseSession,
    ) -> ConversationAccepted:
        with db.begin():
            thread_id = create_thread_for_message(db, principal=principal, message_id=message.client_message_id)
            accepted = accept_message(db, thread_id=thread_id, message=message, principal=principal, key=key)
            if accepted.outcome == "unavailable":
                raise HTTPException(404)
            if accepted.outcome == "message_conflict":
                return _error(409, "message_conflict", "Send the updated message as a new request.")
            if accepted.outcome != "accepted":
                raise ConversationBusy()
        return ConversationAccepted(thread_id=thread_id, run_id=accepted.run_id, accepted_revision=accepted.accepted_revision)

    @router.post(THREAD_PATH + "/messages", status_code=202, responses={409: {"model": AgentHttpError}})
    def continue_thread(
        thread_id: UUID, message: SendMessage, principal: AuthenticatedOwner, db: DatabaseSession,
    ) -> CaseTaskAccepted:
        with db.begin():
            accepted = accept_message(db, thread_id=thread_id, message=message, principal=principal, key=key)
        if accepted.outcome == "unavailable":
            raise HTTPException(404)
        if accepted.outcome == "active_run":
            raise ConversationBusy()
        if accepted.outcome == "stale_thread":
            return _error(409, "stale_thread", "Reopen the conversation and try again.")
        if accepted.outcome == "message_conflict":
            return _error(409, "message_conflict", "Send the updated message as a new request.")
        return CaseTaskAccepted(run_id=accepted.run_id, accepted_revision=accepted.accepted_revision)

    @router.get(RUN_PATH)
    def run_snapshot(
        thread_id: UUID, run_id: UUID, principal: AuthenticatedOwner, db: DatabaseSession,
    ) -> RunSnapshot:
        snapshot = read_run_snapshot(db, thread_id=thread_id, run_id=run_id, principal=principal, key=key)
        if snapshot is None:
            raise HTTPException(404)
        handoff = read_run_handoff(db, snapshot, principal=principal, key=key, read_evidence_scope=read_evidence_scope)
        return snapshot.model_copy(update={"handoff": handoff})

    @router.get(RUN_PATH + "/events")
    def replay_events(
        thread_id: UUID, run_id: UUID, principal: AuthenticatedOwner, db: DatabaseSession,
        after_seq: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=100)] = 100,
    ) -> EventPage:
        page = read_run_events(
            db, thread_id=thread_id, run_id=run_id, principal=principal,
            key=key, after_seq=after_seq, limit=limit,
        )
        if page is None:
            raise HTTPException(404)
        return page

    @router.get(RUN_PATH + "/sources/{citation_id}")
    def source_card(
        thread_id: UUID, run_id: UUID, citation_id: PassageId,
        principal: AuthenticatedOwner, db: DatabaseSession,
    ) -> RunSourceCard:
        card = read_run_source_card(
            db, thread_id=thread_id, run_id=run_id, citation_id=citation_id, principal=principal, key=key,
        )
        if card is None:
            raise HTTPException(404)
        return card

    @router.post(RUN_PATH + "/stop", responses={409: {"model": AgentHttpError}})
    def stop_owned_run(
        thread_id: UUID, run_id: UUID, payload: StopRun, principal: AuthenticatedOwner, db: DatabaseSession,
    ) -> RunSnapshot:
        with db.begin():
            snapshot = stop_run(
                db, thread_id=thread_id, run_id=run_id, principal=principal, key=key,
                expected_run_revision=payload.expected_run_revision,
            )
            if snapshot is None:
                raise HTTPException(404)
        return snapshot

    @router.post(RUN_PATH + "/questions/{question_id}/reply", responses={409: {"model": AgentHttpError}})
    def reply_to_question(
        thread_id: UUID, run_id: UUID, question_id: UUID, reply: ClarificationReply,
        principal: AuthenticatedOwner, db: DatabaseSession,
    ) -> QuestionAnswered:
        with db.begin():
            event = submit_clarification_reply(
                db, thread_id=thread_id, run_id=run_id, question_id=question_id,
                principal=principal, key=key, reply=reply,
            )
            if event is None:
                raise HTTPException(404)
        return event

    @router.post(RUN_PATH + "/proposals/{proposal_id}/decision", responses={409: {"model": AgentHttpError}})
    def decide_proposal(
        thread_id: UUID, run_id: UUID, proposal_id: UUID, payload: SubmitProposalDecision,
        principal: AuthenticatedOwner, db: DatabaseSession, request: Request,
    ) -> ApprovalDecided:
        with db.begin():
            event = submit_proposal_decision(
                db, thread_id=thread_id, run_id=run_id, proposal_id=proposal_id, principal=principal,
                key=key, payload=payload,
            )
            if event is None:
                raise HTTPException(404)
        if case_updates is not None and event.decision.decision == "accept":
            resume_approved_case_update(
                request.app.state.session_factory, thread_id=thread_id, run_id=run_id, principal=principal,
                key=key, updates=case_updates, acceptance=event,
            )
        return event

    return router
