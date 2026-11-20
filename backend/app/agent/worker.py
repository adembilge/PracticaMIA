"""Advance one durable step of an owned run in the internal agent service."""

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from app.agent.answer_evidence import AnswerEvidenceScopeReader, revalidate_answer_evidence
from app.agent.approval_graph import pause_for_approval
from app.agent.case_context import read_shared_citizenship, read_worker_case_context
from app.agent.case_selection import resolve_saved_case
from app.agent.catalogue_evidence import CatalogueUnavailable, corrected_query_kind, refresh_corrected_evidence
from app.agent.checkpoints import (
    CheckpointConflict, CheckpointState, finish_checkpoint, load_checkpoint, save_checkpoint,
)
from app.agent.contract import (
    AnswerCompleted, AnswerResult, ApprovalApplied, ApprovalProposal, ApprovalRequested,
    ClarifyingQuestion, DocumentObservation,
    NextAction, ProgressUpdated, QuestionAnswered, QuestionRequested, RunFailed, RunSnapshot, RunStarted,
)
from app.agent.diagnostics import AgentFailureDiagnostic
from app.agent.destination_correction import reassess_destination
from app.agent.proposal_freshness import ProposalFreshness, proposal_evidence_fingerprint
from app.agent.run_events import EventConflict, _read_event_at, read_run_snapshot
from app.agent.run_requests import (
    WORKER_RUN_STATUSES, AgentRunRequest, StoredMessage, _owned_run, read_recent_user_messages, read_run_message,
)
from app.agent.tool_access import ToolAccessDenied
from app.agent.tool_contract import ReadCaseContext
from app.agent.tool_execution import check_tool_execution
from app.agent.worker_leases import WorkerLease, WorkerLeaseConflict, claim_next_run, require_worker_lease
from app.auth.tokens import Principal
from app.cases.intake_schemas import IntakeFacts
from app.config import Settings
from app.rules.engine import JURISDICTION, PROCEDURE


@dataclass(frozen=True)
class RequestClarification:
    question: ClarifyingQuestion
    resume_state: CheckpointState


@dataclass(frozen=True)
class RequestApproval:
    proposal: ApprovalProposal
    resume_state: CheckpointState


class ModelProviderTimeout(TimeoutError):
    """Signal that the execution adapter's model request reached its deadline."""


ExecuteStep = Callable[
    [StoredMessage, CheckpointState], CheckpointState | RequestClarification | RequestApproval | AnswerResult,
]


def run_next_worker_step(
    sessions: sessionmaker[Session], *, key: bytes, lease_for: timedelta, execute: ExecuteStep,
    document_settings: Settings | None = None,
    read_evidence_scope: AnswerEvidenceScopeReader | None = None,
) -> RunSnapshot | None:
    """Claim and advance one eligible run, leaving crash recovery to its lease."""
    with sessions.begin() as db:
        lease = claim_next_run(db, lease_for=lease_for)
    if lease is None:
        return None
    return run_worker_step(
        sessions, thread_id=lease.thread_id, run_id=lease.run_id, principal=lease.principal,
        key=key, execute=execute, lease=lease, document_settings=document_settings,
        read_evidence_scope=read_evidence_scope,
    )


def run_worker_batch(
    sessions: sessionmaker[Session], *, key: bytes, lease_for: timedelta,
    execute: ExecuteStep, max_steps: int, document_settings: Settings | None = None,
    read_evidence_scope: AnswerEvidenceScopeReader | None = None,
) -> int:
    """Process up to the caller's attempt budget and return the recorded step count."""
    if max_steps < 1:
        raise ValueError("A worker batch requires a positive step budget")

    recorded_steps = 0
    for _ in range(max_steps):
        try:
            snapshot = run_next_worker_step(
                sessions, key=key, lease_for=lease_for, execute=execute, document_settings=document_settings,
                read_evidence_scope=read_evidence_scope,
            )
        except WorkerLeaseConflict:
            # A replacement worker may already own this run. A lost lease still
            # consumes an attempt so contention cannot keep the batch running.
            continue
        if snapshot is None:
            break
        recorded_steps += 1
    return recorded_steps


def run_worker_step(
    sessions: sessionmaker[Session], *, thread_id: UUID, run_id: UUID,
    principal: Principal, key: bytes,
    execute: ExecuteStep, lease: WorkerLease | None = None,
    document_settings: Settings | None = None,
    read_evidence_scope: AnswerEvidenceScopeReader | None = None,
) -> RunSnapshot | None:
    """Run a side-effect-free step between short database transactions."""
    context = {"thread_id": thread_id, "run_id": run_id, "principal": principal, "key": key}
    with sessions.begin() as db:
        # Use an exclusive lock before initializing so two workers never need
        # to upgrade a shared lock on the same queued run.
        run = db.scalar(_owned_run(thread_id, run_id, principal).with_for_update(
            of=AgentRunRequest,
        ))
        if run is None:
            return None
        require_worker_lease(db, run, lease)
        if run.status not in WORKER_RUN_STATUSES:
            return read_run_snapshot(db, **context)
        checkpoint = load_checkpoint(db, **context)
        if run.status == "queued":
            if checkpoint is not None:
                raise CheckpointConflict("Queued run already has a checkpoint")
            started = RunStarted(
                schema_version=1, thread_id=thread_id, run_id=run_id, event_seq=1,
                occurred_at=datetime.now(timezone.utc), type="run.started",
                client_message_id=UUID(run.client_message_id),
            )
            checkpoint = save_checkpoint(
                db, **context, expected_revision=0, expected_event_seq=0,
                state=CheckpointState(next_node="load_context"), event=started,
            )
        if checkpoint is None:
            raise CheckpointConflict("Running worker has no checkpoint")
        message = read_run_message(db, **context)
        if message is None:
            return None
        boundary_event = _read_event_at(db, run, checkpoint.event_seq, principal, key)
        reply = boundary_event if isinstance(boundary_event, QuestionAnswered) else None
        question = None
        if reply is not None:
            requested = _read_event_at(db, run, reply.event_seq - 1, principal, key)
            if not isinstance(requested, QuestionRequested) or requested.question.question_id != reply.question_id:
                raise CheckpointConflict("A clarification reply requires its recorded question")
            question = requested.question
        topic_changed = reply is not None and reply.disposition == "change_topic"
        case_question = question is not None and bool(question.case_choices)
        resume_case = checkpoint.state.next_node == "choose_next_step" and checkpoint.state.intent == "resume_case"
        resolve_case = not topic_changed and (case_question or resume_case)

        case_context = None
        choosing_goal = checkpoint.state.next_node == "choose_next_step" and bool(checkpoint.state.goals)
        if message.case_id is not None and not topic_changed and not resolve_case and not choosing_goal:
            try:
                check_tool_execution(
                    db, principal=principal, thread_id=thread_id, run_id=run_id,
                    call=ReadCaseContext(tool="read_case_context", case_id=message.case_id),
                )
            except ToolAccessDenied:
                AgentFailureDiagnostic(
                    code="tool_denied", stage=checkpoint.state.next_node, intent=checkpoint.state.intent,
                    tool="read_case_context",
                ).emit()
                return None
            case_context = read_worker_case_context(
                db, thread_id=thread_id, case_id=message.case_id, principal=principal,
                document_settings=document_settings if checkpoint.state.next_node == "choose_next_step" else None,
            )
            if case_context is None:
                return None
            if (
                checkpoint.state.next_node == "choose_next_step"
                and checkpoint.state.procedure_candidates == [PROCEDURE]
                and case_context.user_confirmed_facts is None
            ):
                case_context = replace(case_context, shared_citizenship_class=read_shared_citizenship(
                    db, thread_id=thread_id, case_id=message.case_id, principal=principal,
                ))

        message = replace(
            message,
            clarification_reply=reply,
            clarification_question=question,
            approval_applied=boundary_event if isinstance(boundary_event, ApprovalApplied) else None,
            recent_user_messages=() if topic_changed else read_recent_user_messages(
                db, run=run, principal=principal, key=key,
            ),
            case_context=case_context,
        )

    # Only completed boundaries survive a crash. Uncommitted computation can
    # run again, so this callback must not perform external writes.
    corrections = checkpoint.state.routing_corrections
    destination_correction = message.destination_correction
    destination_pending = destination_correction is not None and destination_correction.needs_confirmation(
        case_context.intake_confirmed_at if case_context is not None else None,
    )
    if topic_changed and question is not None:
        explanation, label = (
            ("The previous question is still open. Send a new message to change topics.", "Start a new topic")
            if message.language == "en" else
            ("La domanda precedente resta aperta. Invia un nuovo messaggio per cambiare argomento.", "Cambia argomento")
        )
        result = AnswerResult(
            explanation=explanation, verification_status="insufficient_evidence",
            missing_information=question.missing_fields,
            next_action=NextAction(label=label, operation="start_new_topic"),
        )
    elif resolve_case:
        goal_selection = question.case_goal if case_question else None
        result = AnswerResult(
            explanation="Choose a saved case." if message.language == "en" else "Scegli una pratica salvata.",
            verification_status="insufficient_evidence",
            missing_information=(
                checkpoint.state.goals[goal_selection.active_goal - 1].missing_fields
                if goal_selection is not None else ["case_reference"]
            ),
            goals=checkpoint.state.goals,
            goal_selection=goal_selection,
        )
    elif message.corrects_destination and checkpoint.state.next_node == "choose_next_step":
        result = reassess_destination(message.language)
    elif destination_pending and checkpoint.state.next_node in ("find_evidence", "verify_and_respond") and (
        corrections is None or corrections.destination in (None, JURISDICTION)
    ):
        result = reassess_destination(message.language)
    elif checkpoint.state.next_node == "find_evidence" and corrections:
        for attempt in range(2):
            try:
                with sessions() as db:
                    result = refresh_corrected_evidence(
                        db, state=checkpoint.state, thread_id=thread_id, run_id=run_id, case_id=message.case_id,
                        principal=principal, query=message.text, language=message.language,
                    )
                break
            except CatalogueUnavailable as failure:
                if attempt == 1:
                    result = failure
            except ToolAccessDenied:
                AgentFailureDiagnostic(
                    code="tool_denied", stage=checkpoint.state.next_node, intent=checkpoint.state.intent,
                    query_kind=corrected_query_kind(corrections),
                    tool="find_evidence",
                ).emit()
                return None
    else:
        try:
            result = execute(message, checkpoint.state.model_copy(deep=True))
        except ModelProviderTimeout as failure:
            result = failure
    diagnostic = None
    with sessions.begin() as db:
        run = db.scalar(_owned_run(thread_id, run_id, principal).with_for_update(
            of=AgentRunRequest,
        ))
        if run is None:
            return None
        require_worker_lease(db, run, lease)
        if (
            case_context is not None and case_context.shared_citizenship_class is not None
            and read_shared_citizenship(
                db, thread_id=thread_id, case_id=case_context.case_id, principal=principal,
            ) != case_context.shared_citizenship_class
        ):
            # Drop this computation. The next worker can resolve the same step with current facts.
            if lease is not None:
                run.lease_token = None
                run.lease_expires_at = None
            return None
        if isinstance(result, AnswerResult) and (
            resolve_case or (result.goal_selection and result.goal_selection.active_goal)
        ):
            resolved = resolve_saved_case(
                db, thread_id=thread_id, principal=principal, message=message, answer=result, resume_case=resume_case,
            )
            result = RequestClarification(resolved, checkpoint.state) if isinstance(resolved, ClarifyingQuestion) else resolved
        proposal_state = None
        if isinstance(result, RequestApproval):
            if str(result.proposal.case_id) != run.case_id:
                raise EventConflict("Proposal must belong to the run's case")
            case_fingerprint = case_context.proposal_case_fingerprint if case_context else None
            field_id = result.proposal.field_id
            checklist_evidence = () if field_id in IntakeFacts.model_fields else (
                case_context.checklist_evidence_ids.get(field_id) if case_context else None
            )
            evidence_ids = sorted(set(checkpoint.state.evidence_ids).union(
                result.resume_state.evidence_ids, checklist_evidence or (),
            ))
            evidence_fingerprint = (
                proposal_evidence_fingerprint(db, evidence_ids)
                if case_fingerprint is not None and checklist_evidence is not None else None
            )
            if case_fingerprint is None or evidence_fingerprint is None:
                explanation, label = (
                    ("Review the case and current sources before requesting this change again.", "Review case details")
                    if message.language == "en" else
                    ("Rivedi la pratica e le fonti attuali prima di richiedere di nuovo la modifica.",
                     "Rivedi i dati della pratica")
                )
                result = AnswerResult(
                    explanation=explanation, verification_status="insufficient_evidence",
                    next_action=NextAction(label=label, operation="provide_information"),
                )
            else:
                proposal_state = result.resume_state.model_copy(update={
                    "pending_proposal_id": result.proposal.proposal_id,
                    "approval_pause": pause_for_approval(thread_id, run_id, result.proposal.proposal_id),
                    "proposal_freshness": ProposalFreshness(
                        case_fingerprint=case_fingerprint, passage_ids=evidence_ids,
                        evidence_fingerprint=evidence_fingerprint,
                    ),
                })
        if isinstance(result, AnswerResult):
            if (checkpoint.state.uses_confirmed_case_scope or destination_correction is not None) and (
                result.citations or result.official_channel
            ):
                current_case = read_worker_case_context(
                    db, thread_id=thread_id, case_id=message.case_id, principal=principal, lock_case=True,
                ) if message.case_id is not None else None
                if destination_correction is not None and destination_correction.needs_confirmation(
                    current_case.intake_confirmed_at if current_case is not None else None,
                ):
                    result = reassess_destination(message.language)
                elif checkpoint.state.uses_confirmed_case_scope and (
                    not result.citations or current_case is None or not current_case.matches_first_milan_route
                ):
                    explanation, label = (
                        ("Review and confirm the saved case details before checking the filing step.", "Review case details")
                        if message.language == "en" else
                        ("Rivedi e conferma i dati della pratica prima di verificare l’invio.", "Rivedi i dati della pratica")
                    )
                    result = AnswerResult(
                        explanation=explanation, verification_status="insufficient_evidence",
                        next_action=NextAction(label=label, operation="provide_information"),
                    )
            if result.citations:
                scope = (
                    read_evidence_scope(db, thread_id, run_id, message.case_id, principal)
                    if read_evidence_scope is not None else None
                )
                draft = result
                result = revalidate_answer_evidence(db, draft, scope=scope, language=message.language)
                if (
                    result.verification_status != draft.verification_status or result.citations != draft.citations
                    or result.claims != draft.claims or result.official_channel != draft.official_channel
                ):
                    scoped_passages = {
                        assignment.evidence_ref for assignment in scope.assignments
                        if assignment.approved_for_routing and assignment.procedure_id == scope.procedure_id
                    } if scope is not None else set()
                    versions = tuple(sorted({
                        citation.source_version_id for citation in draft.citations
                        if citation.passage_id in scoped_passages
                    }))
                    diagnostic = AgentFailureDiagnostic(
                        code="evidence_revalidation_failed", stage=checkpoint.state.next_node,
                        intent=checkpoint.state.intent, source_version_ids=versions,
                    )

            relevant_fields = set(result.missing_information).union(checkpoint.state.missing_fields)
            if question is not None:
                relevant_fields.update(question.missing_fields)
            observations = []
            # Document provenance comes from a fresh owned-case read, including after clarification.
            if (
                case_context is not None and relevant_fields and document_settings is not None
                and document_settings.enable_private_document_api
            ):
                current_case = read_worker_case_context(
                    db, thread_id=thread_id, case_id=case_context.case_id, principal=principal,
                    document_settings=document_settings,
                )
                if current_case is not None:
                    observations = [
                        DocumentObservation(field_id=field_id, status=status)
                        for field_id, status in sorted(current_case.document_fields.items())
                        if field_id in relevant_fields
                    ]
            result = result.model_copy(update={"document_observations": observations})
        boundary = {
            "expected_revision": checkpoint.revision,
            "expected_event_seq": checkpoint.event_seq,
        }
        envelope = {
            "schema_version": 1, "thread_id": thread_id, "run_id": run_id,
            "event_seq": checkpoint.event_seq + 1, "occurred_at": datetime.now(timezone.utc),
        }
        if isinstance(result, (CatalogueUnavailable, ModelProviderTimeout)):
            if isinstance(result, CatalogueUnavailable):
                diagnostic = AgentFailureDiagnostic(
                    code="catalogue_unavailable", stage=checkpoint.state.next_node, intent=checkpoint.state.intent,
                    query_kind=corrected_query_kind(corrections),
                    tool="find_evidence",
                )
            else:
                diagnostic = AgentFailureDiagnostic(
                    code="provider_unavailable", stage=checkpoint.state.next_node, intent=checkpoint.state.intent,
                    query_kind="model_request",
                )
            terminal = RunFailed(
                **envelope, type="run.failed", code=diagnostic.code, retryable=True, recovery="retry_later",
            )
            finish_checkpoint(db, principal=principal, key=key, **boundary, event=terminal)
        elif isinstance(result, AnswerResult):
            terminal = AnswerCompleted(**envelope, type="answer.completed", result=result)
            finish_checkpoint(db, principal=principal, key=key, **boundary, event=terminal)
        else:
            if isinstance(result, RequestClarification):
                state = result.resume_state.model_copy(
                    update={"pending_question_id": result.question.question_id},
                )
                event = QuestionRequested(**envelope, type="question.requested", question=result.question)
            elif isinstance(result, RequestApproval):
                assert proposal_state is not None
                state = proposal_state
                event = ApprovalRequested(
                    **envelope, type="approval.requested", proposal=result.proposal, requires_recorded_decision=True,
                )
            else:
                state = result
                event = ProgressUpdated(
                    **envelope, type="progress.updated", stage=checkpoint.state.next_node,
                    text="Worker step recorded.",
                )
            save_checkpoint(db, **context, **boundary, state=state, event=event)
        if lease is not None:
            run.lease_token = None
            run.lease_expires_at = None
        snapshot = read_run_snapshot(db, **context)
    if diagnostic is not None:
        diagnostic.emit()
    return snapshot
