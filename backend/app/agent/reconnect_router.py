"""Authenticated Phase 4 transport, mounted only in the isolated HTTP tests."""

from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session

from app.agent.checkpoints import CheckpointConflict, submit_clarification_reply
from app.agent.contract import ClarificationReply, ContractModel, EventPage, QuestionAnswered, RunSnapshot
from app.agent.run_events import (
    EventConflict, InvalidClarificationReply, InvalidEventCursor, read_run_events, read_run_snapshot,
)
from app.agent.run_requests import _payload_cipher
from app.auth.tokens import Principal, get_principal
from app.database import get_session

AuthenticatedOwner = Annotated[Principal, Depends(get_principal)]
DatabaseSession = Annotated[Session, Depends(get_session)]


ErrorCode = Literal[
    "unauthenticated", "unavailable", "invalid_request", "invalid_cursor", "invalid_reply", "stale_question",
]


class AgentHttpError(ContractModel):
    code: ErrorCode
    message: str
    request_id: UUID


def _error(status: int, code: ErrorCode, message: str, *, headers=None) -> JSONResponse:
    error = AgentHttpError(code=code, message=message, request_id=uuid4())
    return JSONResponse(error.model_dump(mode="json"), status_code=status, headers=headers)


class _PrivateAgentRoute(APIRoute):
    def get_route_handler(self):
        handle = super().get_route_handler()

        async def private_response(request: Request):
            try:
                response = await handle(request)
            except RequestValidationError:
                response = _error(422, "invalid_request", "Check the request parameters.")
            except InvalidEventCursor:
                response = _error(422, "invalid_cursor", "Use a cursor from this run.")
            except InvalidClarificationReply:
                response = _error(422, "invalid_reply", "Select one of the offered choices.")
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


def build_reconnect_router(*, key: bytes) -> APIRouter:
    """Build the transport with a key supplied by the isolated application."""
    _payload_cipher(key)
    router = APIRouter(
        prefix="/api/v1/agent/threads/{thread_id}/runs/{run_id}",
        route_class=_PrivateAgentRoute,
        responses={status: {"model": AgentHttpError} for status in (401, 404, 422)},
    )

    @router.get("")
    def run_snapshot(
        thread_id: UUID, run_id: UUID, principal: AuthenticatedOwner, db: DatabaseSession,
    ) -> RunSnapshot:
        snapshot = read_run_snapshot(db, thread_id=thread_id, run_id=run_id, principal=principal, key=key)
        if snapshot is None:
            raise HTTPException(404)
        return snapshot

    @router.get("/events")
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

    @router.post("/questions/{question_id}/reply", responses={409: {"model": AgentHttpError}})
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

    return router
