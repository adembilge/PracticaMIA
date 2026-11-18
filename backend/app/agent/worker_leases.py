"""Claim internal agent work and reject writes from superseded workers."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.agent.checkpoints import AgentRunCheckpoint
from app.agent.run_events import AgentRunEvent
from app.agent.run_requests import AgentRunRequest, WORKER_RUN_STATUSES
from app.agent.threads import AgentThread, AgentThreadCase
from app.auth.tokens import Principal
from app.cases.model import CaseRecord


@dataclass(frozen=True)
class WorkerLease:
    thread_id: UUID
    run_id: UUID
    principal: Principal
    token: UUID


class WorkerLeaseConflict(ValueError):
    """The run is leased to another worker or its lease expired."""


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _database_now(db: Session) -> datetime:
    clock = func.clock_timestamp() if db.get_bind().dialect.name == "postgresql" else func.current_timestamp()
    return _utc(db.scalar(select(clock)))


def claim_next_run(db: Session, *, lease_for: timedelta) -> WorkerLease | None:
    """Reserve the oldest runnable run until the caller releases it or it expires."""
    if lease_for <= timedelta(0):
        raise ValueError("The worker lease duration must be positive")

    now = _database_now(db)
    latest_event = (
        select(func.max(AgentRunEvent.event_seq))
        .where(AgentRunEvent.run_id == AgentRunRequest.id)
        .correlate(AgentRunRequest)
        .scalar_subquery()
    )
    ready_checkpoint = (
        select(AgentRunCheckpoint.run_id)
        .where(
            AgentRunCheckpoint.run_id == AgentRunRequest.id,
            AgentRunCheckpoint.event_seq == latest_event,
        )
        .exists()
    )
    found = db.execute(
        select(AgentRunRequest, AgentThread.owner_subject)
        .join(AgentThread)
        .outerjoin(AgentThreadCase, and_(
            AgentThreadCase.thread_id == AgentRunRequest.thread_id,
            AgentThreadCase.case_id == AgentRunRequest.case_id,
        ))
        .outerjoin(CaseRecord, and_(
            CaseRecord.id == AgentThreadCase.case_id,
            CaseRecord.owner_subject == AgentThread.owner_subject,
        ))
        .where(
            AgentRunRequest.status.in_(WORKER_RUN_STATUSES),
            (AgentRunRequest.status == "queued") | ready_checkpoint,
            AgentRunRequest.case_id.is_(None) | CaseRecord.id.is_not(None),
            or_(AgentRunRequest.lease_token.is_(None), AgentRunRequest.lease_expires_at <= now),
        )
        .order_by(AgentRunRequest.accepted_at, AgentRunRequest.id)
        .limit(1)
        .execution_options(populate_existing=True)
        .with_for_update(of=AgentRunRequest, skip_locked=True)
    ).one_or_none()
    if found is None:
        return None

    run, owner = found
    token = uuid4()
    run.lease_token = str(token)
    run.lease_expires_at = now + lease_for
    db.flush()
    return WorkerLease(UUID(run.thread_id), UUID(run.id), Principal(owner), token)


def require_worker_lease(db: Session, run: AgentRunRequest, lease: WorkerLease | None) -> None:
    """Check the token on the locked run before executing or committing a step."""
    if lease is None:
        if run.lease_token is not None:
            raise WorkerLeaseConflict("The run requires its worker lease")
        return
    if (
        run.lease_token != str(lease.token)
        or run.lease_expires_at is None
        or _utc(run.lease_expires_at) <= _database_now(db)
    ):
        raise WorkerLeaseConflict("The worker lease is no longer current")
