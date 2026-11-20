"""Content-free monitoring records for the isolated conversation agent."""

import logging
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.agent.contract import AgentIntent, AgentNode, ContractModel


logger = logging.getLogger(__name__)

EvidenceQueryKind = Literal["message_lexical", "procedure_hint"]


class AgentFailureDiagnostic(ContractModel):
    """Keep the record limited to code-owned labels and public registry version IDs."""

    event: Literal["agent_failure"] = "agent_failure"
    schema_version: Literal[1] = 1
    code: Literal[
        "catalogue_unavailable", "catalogue_invalid_query", "catalogue_evidence_unavailable",
        "provider_unavailable", "evidence_revalidation_failed", "proposal_outdated", "tool_denied",
    ]
    stage: AgentNode | Literal["resume_approval"]
    intent: AgentIntent | None = None
    query_kind: EvidenceQueryKind | Literal["model_request"] | None = None
    tool: Literal["read_case_context", "find_evidence", "apply_approved_update"] | None = None
    source_version_ids: tuple[UUID, ...] = Field(default=(), max_length=30)

    def emit(self) -> None:
        logger.warning("%s", self.model_dump_json())
