"""The side-effect-free LangGraph approval gate."""

from typing import Literal, TypedDict, cast
from uuid import UUID

from langgraph.checkpoint.base import Checkpoint, CheckpointMetadata
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, Interrupt, interrupt
from pydantic import Field, JsonValue

from app.agent.contract import ApprovalDecided, ContractModel


class ApprovalGraphConflict(ValueError):
    """The approval cannot resume this checkpoint."""


class ApprovalPause(ContractModel):
    format_version: Literal[1] = 1
    thread_id: UUID
    run_id: UUID
    checkpoint: dict[str, JsonValue]
    metadata: dict[str, JsonValue]
    task_id: str = Field(min_length=1, max_length=80)
    interrupt_id: str = Field(min_length=1, max_length=80)


class ApprovalState(TypedDict, total=False):
    proposal_id: str
    decision_id: str


def _await_approval(state: ApprovalState) -> ApprovalState:
    return {"decision_id": interrupt(state["proposal_id"])}


_graph = StateGraph(ApprovalState)
_graph.add_node("await_approval", _await_approval)
_graph.add_edge(START, "await_approval")
_graph.add_edge("await_approval", END)


def _config(thread_id: UUID):
    return {"configurable": {"thread_id": str(thread_id), "checkpoint_ns": ""}}


def pause_for_approval(thread_id: UUID, run_id: UUID, proposal_id: UUID) -> ApprovalPause:
    saver = InMemorySaver()
    graph = _graph.compile(checkpointer=saver)
    config = _config(thread_id)
    graph.invoke({"proposal_id": str(proposal_id)}, config)
    saved = saver.get_tuple(config)
    if saved is None or len(saved.pending_writes or ()) != 1:
        raise ApprovalGraphConflict("Expected one pending approval interrupt")
    task_id, channel, interrupts = saved.pending_writes[0]
    if channel != "__interrupt__" or len(interrupts) != 1 or interrupts[0].value != str(proposal_id):
        raise ApprovalGraphConflict("Interrupt did not identify the pending proposal")
    return ApprovalPause(
        thread_id=thread_id, run_id=run_id,
        checkpoint=saved.checkpoint, metadata=saved.metadata,
        task_id=task_id, interrupt_id=interrupts[0].id,
    )


def resume_approval(pause: ApprovalPause, accepted: ApprovalDecided) -> None:
    """Restore the original interrupt in the owned conversation and feed it the recorded acceptance."""
    proposal_id = str(accepted.proposal_id)
    config = _config(accepted.thread_id)
    checkpoint = cast(Checkpoint, pause.checkpoint)
    metadata = cast(CheckpointMetadata, pause.metadata)
    if (
        accepted.decision.decision != "accept"
        or checkpoint["channel_values"].get("proposal_id") != proposal_id
        or (pause.thread_id, pause.run_id) != (accepted.thread_id, accepted.run_id)
    ):
        raise ApprovalGraphConflict("Acceptance must refer to the interrupted proposal")

    saver = InMemorySaver()
    graph = _graph.compile(checkpointer=saver)
    config = saver.put(config, checkpoint, metadata, checkpoint["channel_versions"])
    saver.put_writes(
        config, [("__interrupt__", [Interrupt(value=proposal_id, id=pause.interrupt_id)])], pause.task_id,
    )
    decision_id = str(accepted.decision.client_decision_id)
    result = graph.invoke(Command(resume={pause.interrupt_id: decision_id}), config)
    if result.get("decision_id") != decision_id or result.get("__interrupt__"):
        raise ApprovalGraphConflict("The graph did not complete the approval gate")
