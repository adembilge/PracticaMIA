"""Typed agent tool boundary. Parsing a call does not execute it."""

from collections.abc import Set
from typing import Annotated, Literal
from uuid import UUID

from pydantic import ConfigDict, Field, TypeAdapter, field_validator, model_validator

from app.agent.case_context import CaseNextAction
from app.agent.contract import (
    ApprovalProposal, Citation, ContractModel, Identifier, Language, OfficialChannel,
    PassageId, PositiveInt, ShortText,
)
from app.cases.intake_schemas import IntakeFacts
from app.knowledge.entity_matching import MAX_NAME_QUERY_LENGTH, normalize_name
from app.knowledge.html_extraction import MAX_PASSAGE_CHARS
from app.knowledge.search import normalize_query


class CatalogueScope(ContractModel):
    procedure_id: Identifier
    location_id: Identifier


class FindProcedure(ContractModel):
    tool: Literal["find_procedure"]
    query: str = Field(min_length=1, max_length=MAX_NAME_QUERY_LENGTH)
    language: Language
    location_id: Identifier | None = None

    @field_validator("query")
    @classmethod
    def require_search_terms(cls, query: str) -> str:
        if not normalize_name(query):
            raise ValueError("Name query must contain letters or numbers")
        return query


class FindEvidence(ContractModel):
    tool: Literal["find_evidence"]
    case_id: UUID
    scope: CatalogueScope
    query: str = Field(min_length=1, max_length=180)
    limit: Annotated[int, Field(strict=True, ge=1, le=10)] = 5

    @field_validator("query")
    @classmethod
    def require_search_terms(cls, query: str) -> str:
        normalize_query(query)
        return query


class OpenSourceDetails(ContractModel):
    tool: Literal["open_source_details"]
    case_id: UUID
    scope: CatalogueScope
    citation_id: PassageId


class ReadCaseContext(ContractModel):
    tool: Literal["read_case_context"]
    case_id: UUID


class SetIntakeFact(ContractModel):
    kind: Literal["set_intake_fact"]
    facts: IntakeFacts

    @model_validator(mode="after")
    def require_one_value(self):
        if len(self.facts.model_fields_set) != 1 or not self.facts.model_dump(exclude_none=True):
            raise ValueError("An intake proposal must contain one typed fact value")
        return self


class MarkChecklistItem(ContractModel):
    kind: Literal["mark_checklist_item"]
    item_id: Identifier
    reviewed: bool = Field(strict=True)


class ProposeCaseUpdate(ContractModel):
    tool: Literal["propose_case_update"]
    case_id: UUID
    expected_case_revision: PositiveInt
    change: Annotated[SetIntakeFact | MarkChecklistItem, Field(discriminator="kind")]
    rationale: ShortText


class ApplyApprovedUpdate(ContractModel):
    tool: Literal["apply_approved_update"]
    case_id: UUID
    proposal_id: UUID
    expected_case_revision: PositiveInt
    client_operation_id: UUID


ToolCall = Annotated[
    FindProcedure | FindEvidence | OpenSourceDetails | ReadCaseContext | ProposeCaseUpdate | ApplyApprovedUpdate,
    Field(discriminator="tool"),
]
_tool_call_adapter = TypeAdapter(ToolCall)


def parse_tool_call(payload: object, *, catalogue_scopes: Set[tuple[str, str]]) -> ToolCall:
    """Check ID membership against procedure/location pairs from trusted server data."""
    call = _tool_call_adapter.validate_python(payload)
    if isinstance(call, (FindEvidence, OpenSourceDetails)):
        if (call.scope.procedure_id, call.scope.location_id) not in catalogue_scopes:
            raise ValueError("Unknown procedure and location combination")
    elif isinstance(call, FindProcedure) and call.location_id is not None:
        if not any(location_id == call.location_id for _, location_id in catalogue_scopes):
            raise ValueError("Unknown catalogue location")
    return call


class ProcedureChannel(OfficialChannel):
    channel_id: Identifier
    citation: Citation


class ProcedureCandidate(ContractModel):
    scope: CatalogueScope
    name: ShortText
    authority_ids: tuple[Identifier, ...] = Field(default=(), max_length=10)
    channels: tuple[ProcedureChannel, ...] = Field(default=(), max_length=10)

    @model_validator(mode="after")
    def validate_channel_scope(self):
        expected = (self.scope.procedure_id, self.scope.location_id)
        if any((channel.citation.procedure_id, channel.citation.location_id) != expected for channel in self.channels):
            raise ValueError("Channel evidence must match the procedure and location")
        return self


class FindProcedureResult(ContractModel):
    tool: Literal["find_procedure"]
    candidates: tuple[ProcedureCandidate, ...] = Field(max_length=10)


class CataloguePassage(ContractModel):
    model_config = ConfigDict(frozen=True)

    citation: Citation
    source_revision: PositiveInt
    section_path: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1, max_length=MAX_PASSAGE_CHARS)


class CatalogueEvidence(ContractModel):
    model_config = ConfigDict(frozen=True)

    status: Literal[
        "evidence_found", "insufficient_evidence", "needs_information", "unsupported_scope", "case_unavailable",
    ]
    passages: tuple[CataloguePassage, ...] = Field(default=(), max_length=10)
    missing_fields: tuple[Identifier, ...] = Field(default=(), max_length=12)

    @model_validator(mode="after")
    def validate_status(self):
        if (self.status == "evidence_found") != bool(self.passages):
            raise ValueError("Only a successful evidence result contains passages")
        if (self.status == "needs_information") != bool(self.missing_fields):
            raise ValueError("Only an information gap identifies missing fields")
        return self


class FindEvidenceResult(CatalogueEvidence):
    tool: Literal["find_evidence"]


class OpenSourceDetailsResult(CatalogueEvidence):
    tool: Literal["open_source_details"]
    passages: tuple[CataloguePassage, ...] = Field(default=(), max_length=1)


class ReadCaseContextResult(ContractModel):
    tool: Literal["read_case_context"]
    case_id: UUID
    user_confirmed_facts: IntakeFacts | None
    next_action: CaseNextAction | None
    open_review_action_ids: tuple[Identifier, ...] = Field(max_length=60)


class ProposeCaseUpdateResult(ContractModel):
    tool: Literal["propose_case_update"]
    proposal: ApprovalProposal


class ApplyApprovedUpdateResult(ContractModel):
    tool: Literal["apply_approved_update"]
    case_id: UUID
    proposal_id: UUID
    operation_id: UUID
    case_revision: PositiveInt


ToolResult = Annotated[
    FindProcedureResult | FindEvidenceResult | OpenSourceDetailsResult | ReadCaseContextResult
    | ProposeCaseUpdateResult | ApplyApprovedUpdateResult,
    Field(discriminator="tool"),
]
tool_result_adapter = TypeAdapter(ToolResult)
