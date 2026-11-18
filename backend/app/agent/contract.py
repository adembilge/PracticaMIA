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
    text: ClarificationText


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
    operation: Literal["open_official_channel", "provide_information"] | None = None


class AnswerResult(ContractModel):
    explanation: str = Field(min_length=1, max_length=2000)
    verification_status: Literal[
        "verified", "insufficient_evidence", "conflicting_evidence", "unsupported",
    ]
    next_action: NextAction | None = None
    official_channel: OfficialChannel | None = None
    citations: list[Citation] = Field(default_factory=list, max_length=10)
    missing_information: list[Identifier] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_answer(self):
        if self.verification_status == "verified" and not self.citations:
            raise ValueError("A verified answer must reference an evidence passage")
        if self.next_action and self.next_action.operation == "open_official_channel" and not self.official_channel:
            raise ValueError("Opening a channel requires a channel link")
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


class RunSnapshot(ContractModel):
    thread_id: UUID
    run_id: UUID
    status: RunStatus
    last_event_seq: NonnegativeInt
    run_revision: PositiveInt
    result: AnswerResult | None = None

    @model_validator(mode="after")
    def validate_result(self):
        if (self.status == "completed") != (self.result is not None):
            raise ValueError("Only a completed run carries an answer result")
        return self


class ClarifyingQuestion(ContractModel):
    question_id: UUID
    text: ShortText
    answer_shape: Literal["free_text", "single_choice"]
    options: list[ShortText] = Field(default_factory=list, max_length=10)
    missing_fields: list[Identifier] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def validate_options(self):
        if self.answer_shape == "single_choice":
            if len(set(self.options)) != len(self.options) or len(self.options) < 2:
                raise ValueError("A choice needs at least two distinct options")
        elif self.options:
            raise ValueError("Free-text questions do not include options")
        return self


class ApprovalProposal(ContractModel):
    proposal_id: UUID
    case_id: UUID
    field_id: Identifier
    previous_value: FieldValue | None
    proposed_value: FieldValue
    rationale: ShortText
    expected_case_revision: PositiveInt
    expires_at: AwareDatetime


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
    text: ClarificationText


class ApprovalRequested(EventEnvelope):
    type: Literal["approval.requested"]
    proposal: ApprovalProposal


class AnswerCompleted(EventEnvelope):
    type: Literal["answer.completed"]
    result: AnswerResult


class RunFailed(EventEnvelope):
    type: Literal["run.failed"]
    code: Literal["catalogue_unavailable", "provider_unavailable", "capacity_exceeded", "internal_error"]
    retryable: bool
    recovery: Literal["retry_later", "resume_run", "contact_support"]


class RunStopped(EventEnvelope):
    type: Literal["run.stopped"]
    committed_operation_ids: list[UUID] = Field(max_length=20)


AgentEvent = Annotated[
    RunStarted | ProgressUpdated | QuestionRequested | QuestionAnswered | ApprovalRequested
    | AnswerCompleted | RunFailed | RunStopped,
    Field(discriminator="type"),
]
agent_event_adapter = TypeAdapter(AgentEvent)
TERMINAL_EVENTS = frozenset({"answer.completed", "run.failed", "run.stopped"})


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
            if event.event_seq != seq or (seq == 1) != (event.type == "run.started"):
                raise ValueError("Events must follow the run sequence")
            if event.type in TERMINAL_EVENTS and (seq != self.last_event_seq or self.has_more):
                raise ValueError("A terminal event must end the run")
        return self
