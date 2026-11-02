"""One turn. Retrieval and the rule stay apart."""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class Turn(TypedDict, total=False):
    facts: dict
    query: str
    procedure: str
    jurisdiction: str
    language: str
    evidence: dict
    decision: dict


def build(search=None, evaluate=None):
    def retrieve(state):
        finder = search
        if finder is None:
            from retrieval import search as finder

        return {
            "evidence": finder(
                state["query"],
                state["procedure"],
                state["jurisdiction"],
                state["language"],
            )
        }

    def decide(state):
        judge = evaluate
        if judge is None:
            from rules import evaluate as judge

        return {"decision": judge(state["facts"])}

    graph = StateGraph(Turn)
    graph.add_node("retrieve", retrieve)
    graph.add_node("decide", decide)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "decide")
    graph.add_edge("decide", END)
    return graph.compile()
