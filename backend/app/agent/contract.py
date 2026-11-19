"""Phase 4 Task 31 wire models for offline contract review."""

from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, StringConstraints,
    TypeAdapter, field_validator, model_validator,
)

from app.knowledge.quote_verification import ID as PASSAGE_ID_PATTERN

Language = Literal["it", "en"]
ClaimKind = Literal["authority", "channel", "mandatory_document", "fee", "deadline", "condition", "form_version"]
DocumentFieldStatus = Literal["needs_review", "reviewed", "conflict"]
MAX_ANSWER_EXPLANATION_LENGTH = 2000
MAX_ANSWER_CITATIONS = 10
MAX_ANSWER_CLAIMS = 12
ClarificationDisposition = Literal["answer", "unknown", "skip", "change_topic"]
# An intent describes a user's request. It grants no access or authority.
AgentIntent = Literal[
    "request_information",
    "find_procedure",
    "explain_notice",
    "explain_form_field",
    "resume_case",
    "plan_multiple_tasks",
]
RunStatus = Literal[
    "queued", "running", "waiting_for_information", "waiting_for_approval",
    "stopping", "stopped", "completed", "failed",
]
ShortText = Annotated[str, StringConstraints(min_length=1, max_length=300, strip_whitespace=True)]
ClarificationText = Annotated[str, StringConstraints(min_length=1, max_length=2000, strip_whitespace=True)]
Identifier = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,96}$")]
NonnegativeInt = Annotated[int, Field(strict=True, ge=0)]
PositiveInt = Annotated[int, Field(strict=True, ge=1)]
PassageId = Annotated[str, StringConstraints(pattern=rf"^{PASSAGE_ID_PATTERN}$")]
FieldValue = (
    Annotated[str, StringConstraints(max_length=300)]
    | Annotated[int, Field(strict=True)]
    | Annotated[bool, Field(strict=True)]
)


def require_https(url: HttpUrl) -> HttpUrl:
    if url.scheme != "https" or url.username is not None or url.password is not None:
        raise ValueError("Official links must use HTTPS without credentials")
    return url


OfficialUrl = Annotated[HttpUrl, AfterValidator(require_https)]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SendMessage(ContractModel):
    client_message_id: UUID
    text: str = Field(min_length=1, max_length=2000)
    language: Language
    case_id: UUID | None = None
    expected_thread_revision: PositiveInt | None = None

    @field_validator("text")
    @classmethod
    def require_nonblank_message(cls, text: str) -> str:
        if not text.strip():
            raise ValueError("Message must contain text")
        return text


class ClarificationReply(ContractModel):
    client_reply_id: UUID
    expected_run_revision: int = Field(strict=True, ge=1, le=2_147_483_647)
    text: ClarificationText | None = None
    disposition: ClarificationDisposition = "answer"

    @model_validator(mode="after")
    def validate_disposition(self):
        if (self.disposition == "answer") != (self.text is not None):
            raise ValueError("Only an answer includes reply text")
        return self


class StopRun(ContractModel):
    expected_run_revision: PositiveInt


class ProposalDecision(ContractModel):
    decision: Literal["accept", "correct", "reject", "cancel"]
    expected_case_revision: PositiveInt
    client_decision_id: UUID
    corrected_value: FieldValue | None = None

    @model_validator(mode="after")
    def validate_correction(self):
        if (self.decision == "correct") != (self.corrected_value is not None):
            raise ValueError("Only a correction includes a replacement value")
        return self


class SubmitProposalDecision(ProposalDecision):
    expected_run_revision: int = Field(strict=True, ge=1, le=2_147_483_647)


class OfficialChannel(ContractModel):
    label: ShortText
    url: OfficialUrl


class Citation(ContractModel):
    citation_id: PassageId
    source_id: Identifier
    source_version_id: UUID
    passage_id: PassageId
    official_url: OfficialUrl
    publisher: ShortText
    reviewed_at: AwareDatetime
    procedure_id: Identifier
    location_id: Identifier

    @model_validator(mode="after")
    def validate_passage_identity(self):
        if self.citation_id != self.passage_id or self.passage_id.split(":")[0] != str(self.source_version_id):
            raise ValueError("The citation must identify the exact passage and source version")
        return self


class NextAction(ContractModel):
    label: ShortText
    operation: Literal["open_official_channel", "provide_information", "start_new_topic"] | None = None
    origin: Literal["agent_proposal"] = "agent_proposal"


class EvidenceLinkedClaim(ContractModel):
    kind: ClaimKind
    statement: ShortText
    evidence_ids: list[PassageId] = Field(min_length=1, max_length=10)
    origin: Literal["official_source"] = "official_source"

    @field_validator("evidence_ids")
    @classmethod
    def require_distinct_evidence(cls, ids: list[str]) -> list[str]:
        if len(set(ids)) != len(ids):
            raise ValueError("Claim evidence IDs must be distinct")
        return ids


class DocumentObservation(ContractModel):
    """Owner-scoped review status for a supported field in a user document."""

    field_id: Identifier
    status: DocumentFieldStatus
    origin: Literal["user_document"] = "user_document"


class AnswerResult(ContractModel):
    explanation: str = Field(min_length=1, max_length=MAX_ANSWER_EXPLANATION_LENGTH)
    verification_status: Literal[
        "verified", "insufficient_evidence", "conflicting_evidence", "unsupported",
    ]
    next_action: NextAction | None = None
    official_channel: OfficialChannel | None = None
    citations: list[Citation] = Field(default_factory=list, max_length=MAX_ANSWER_CITATIONS)
    missing_information: list[Identifier] = Field(default_factory=list, max_length=12)
    claims: list[EvidenceLinkedClaim] = Field(default_factory=list, max_length=MAX_ANSWER_CLAIMS)
    document_observations: list[DocumentObservation] = Field(default_factory=list, max_length=12)

    @field_validator("document_observations")
    @classmethod
    def require_distinct_observed_fields(cls, observations: list[DocumentObservation]) -> list[DocumentObservation]:
        if len({item.field_id for item in observations}) != len(observations):
            raise ValueError("Document observations must identify distinct fields")
        return observations

    @model_validator(mode="after")
    def validate_answer(self):
        if self.verification_status == "verified" and not self.citations:
            raise ValueError("A verified answer must reference an evidence passage")
        if self.next_action and self.next_action.operation == "open_official_channel" and not self.official_channel:
            raise ValueError("Opening a channel requires a channel link")
        if self.claims:
            citations = {citation.citation_id for citation in self.citations}
            if len(citations) != len(self.citations):
                raise ValueError("Claim citations must have unique IDs")
            if any(evidence_id not in citations for claim in self.claims for evidence_id in claim.evidence_ids):
                raise ValueError("Each claim evidence ID must identify a citation in the answer")
        return self


def _normalize_cursor_time(value: datetime) -> datetime:
    try:
        return value.astimezone(timezone.utc)
    except OverflowError as exc:
        raise ValueError("Active run cursor time is outside the supported range") from exc


ActiveRunCursorTime = Annotated[AwareDatetime, AfterValidator(_normalize_cursor_time)]


class ActiveRunCursor(ContractModel):
    accepted_at: ActiveRunCursorTime
    run_id: UUID


class ActiveRunSummary(ContractModel):
    run_id: UUID
    thread_id: UUID
    case_id: UUID | None
    status: RunStatus
    accepted_at: AwareDatetime


class ActiveRunPage(ContractModel):
    items: list[ActiveRunSummary] = Field(max_length=50)
    next_cursor: ActiveRunCursor | None = None


class ApprovalProposal(ContractModel):
    proposal_id: UUID
    case_id: UUID
    field_id: Identifier
    previous_value: FieldValue | None
    proposed_value: FieldValue
    rationale: ShortText
    expected_case_revision: PositiveInt
    expires_at: AwareDatetime
    origin: Literal["agent_proposal"] = "agent_proposal"


class RunSnapshot(ContractModel):
    thread_id: UUID
    run_id: UUID
    status: RunStatus
    last_event_seq: NonnegativeInt
    run_revision: PositiveInt
    result: AnswerResult | None = None
    pending_proposal: ApprovalProposal | None = None
    approval_recorded: bool = False

    @model_validator(mode="after")
    def validate_result(self):
        if (self.status == "completed") != (self.result is not None):
            raise ValueError("Only a completed run carries an answer result")
        if self.pending_proposal is not None and self.status != "waiting_for_approval":
            raise ValueError("Only a run awaiting approval carries a pending proposal")
        if self.approval_recorded and (self.status != "waiting_for_approval" or self.pending_proposal is not None):
            raise ValueError("A recorded approval has no open proposal to review")
        return self


class ClarifyingQuestion(ContractModel):
    question_id: UUID
    text: ShortText
    answer_shape: Literal["free_text", "single_choice"]
    options: list[ShortText] = Field(default_factory=list, max_length=10)
    missing_fields: list[Identifier] = Field(min_length=1, max_length=12)
    answer_format: Literal["calendar_date"] | None = None
    reply_hint: ShortText | None = None

    @model_validator(mode="after")
    def validate_options(self):
        if self.answer_shape == "single_choice":
            if len(set(self.options)) != len(self.options) or len(self.options) < 2:
                raise ValueError("A choice needs at least two distinct options")
        elif self.options:
            raise ValueError("Free-text questions do not include options")
        if self.answer_format and (self.answer_shape != "free_text" or len(self.missing_fields) != 1):
            raise ValueError("A formatted reply requires a single free-text field")
        return self


class EventEnvelope(ContractModel):
    schema_version: Literal[1]
    thread_id: UUID
    run_id: UUID
    event_seq: PositiveInt
    occurred_at: AwareDatetime


class RunStarted(EventEnvelope):
    type: Literal["run.started"]
    client_message_id: UUID


class ProgressUpdated(EventEnvelope):
    type: Literal["progress.updated"]
    stage: Identifier
    text: ShortText


class QuestionRequested(EventEnvelope):
    type: Literal["question.requested"]
    question: ClarifyingQuestion


class QuestionAnswered(EventEnvelope):
    type: Literal["question.answered"]
    question_id: UUID
    client_reply_id: UUID
    text: ClarificationText | None = None
    disposition: ClarificationDisposition = "answer"
    origin: Literal["user_entered"] = "user_entered"

    @model_validator(mode="after")
    def validate_answer_text(self):
        if self.disposition == "answer" and self.text is None:
            raise ValueError("An answer includes reply text")
        return self


class ApprovalRequested(EventEnvelope):
    type: Literal["approval.requested"]
    proposal: ApprovalProposal
    requires_recorded_decision: bool = False


class ApprovalDecided(EventEnvelope):
    type: Literal["approval.decided"]
    proposal_id: UUID
    proposal_event_seq: PositiveInt
    decision: ProposalDecision


class ApprovalApplied(EventEnvelope):
    type: Literal["approval.applied"]
    proposal_id: UUID
    operation_id: UUID
    case_revision: PositiveInt


class AnswerCompleted(EventEnvelope):
    type: Literal["answer.completed"]
    result: AnswerResult


class RunFailed(EventEnvelope):
    type: Literal["run.failed"]
    code: Literal[
        "catalogue_unavailable", "provider_unavailable", "capacity_exceeded", "internal_error", "proposal_outdated",
    ]
    retryable: bool
    recovery: Literal["retry_later", "resume_run", "contact_support", "review_proposal"]


class RunStopped(EventEnvelope):
    type: Literal["run.stopped"]
    committed_operation_ids: list[UUID] = Field(max_length=20)


AgentEvent = Annotated[
    RunStarted | ProgressUpdated | QuestionRequested | QuestionAnswered | ApprovalRequested | ApprovalDecided
    | ApprovalApplied | AnswerCompleted | RunFailed | RunStopped,
    Field(discriminator="type"),
]
agent_event_adapter = TypeAdapter(AgentEvent)
TERMINAL_EVENTS = frozenset({"answer.completed", "run.failed", "run.stopped"})


def valid_event_position(event: AgentEvent) -> bool:
    if event.event_seq == 1:
        return event.type in {"run.started", "run.stopped"}
    return event.type != "run.started"


class EventPage(ContractModel):
    thread_id: UUID
    run_id: UUID
    after_seq: NonnegativeInt
    events: list[AgentEvent] = Field(max_length=100)
    last_event_seq: NonnegativeInt
    has_more: bool

    @model_validator(mode="after")
    def validate_page(self):
        if self.last_event_seq != self.after_seq + len(self.events) or (self.has_more and not self.events):
            raise ValueError("The cursor must identify the last returned event")
        for seq, event in enumerate(self.events, start=self.after_seq + 1):
            if event.thread_id != self.thread_id or event.run_id != self.run_id:
                raise ValueError("Events must belong to the requested thread and run")
            if event.event_seq != seq or not valid_event_position(event):
                raise ValueError("Events must follow the run sequence")
            if event.type in TERMINAL_EVENTS and (seq != self.last_event_seq or self.has_more):
                raise ValueError("A terminal event must end the run")
        return self
