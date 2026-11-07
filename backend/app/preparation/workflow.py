"""Bounded read-only LangGraph preparation assessment.

The graph never invokes an LLM, accepts instructions from documents, alters
database state, or submits to government services. Each HTTP request reloads
the owner's confirmed state and revalidates current source approvals.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.rules.engine import evaluate_rules
from app.preparation.document_review import inspect_documents


class PreparationState(TypedDict, total=False):
    case_id: str
    facts: dict
    catalog: dict
    citations_approved: Any
    documents: list[dict]
    rule_result: dict
    document_review: dict
    blocking_issues: list[str]
    status: str
    package: dict | None


def _rules(state: PreparationState) -> dict:
    evaluation = evaluate_rules(
        state["catalog"], state["facts"], state["citations_approved"],
    )
    result = evaluation.as_dict()
    return {"rule_result": result, "blocking_issues": list(result["blocking_issues"])}


def _documents(state: PreparationState) -> dict:
    rule = state["rule_result"]
    documents = state.get("documents", [])
    review = inspect_documents(facts=state["facts"], documents=documents)
    issues = list(state["blocking_issues"])
    # Always surface explicitly confirmed disagreements, even when
    # administrative rules are pending; do NOT unlock the case.
    for conflict in review["conflicts"]:
        issues.append(f"document_conflict:{conflict['field']}")
    if review["unreadable"]:
        issues.append("document_unreadable")
    if rule["decision"] != "supported":
        return {
            "status": rule["decision"],
            "document_review": review,
            "blocking_issues": sorted(set(issues)),
        }
    required = set(rule["required_document_types"])
    approved_types = {
        doc.get("document_type") for doc in documents
        if doc.get("status") == "confirmed"
    }
    for category in sorted(required - approved_types):
        issues.append(f"missing_document:{category}")
    return {
        "status": "needs_review" if review["conflicts"] else
                  "needs_documents" if issues else "reviewable",
        "document_review": review,
        "blocking_issues": sorted(set(issues)),
    }


def _package(state: PreparationState) -> dict:
    if state["status"] != "reviewable" or state["blocking_issues"]:
        return {"package": None}
    docs = [
        {
            "document_id": doc["id"],
            "document_type": doc["document_type"],
            "sha256": doc["sha256"],
            "confirmed_fields": doc.get("confirmed_fields", {}),
        }
        for doc in state["documents"]
        if doc.get("status") == "confirmed"
    ]
    package = {
        "case_id": state["case_id"],
        "jurisdiction": "IT-MI-MILANO",
        "procedure_id": "milan_residence_change",
        "ruleset_version": state["rule_result"]["ruleset_version"],
        "confirmed_facts": state["facts"],
        "checklist": state["rule_result"]["checklist"],
        "evidence_refs": state["rule_result"]["evidence_refs"],
        "documents": sorted(docs, key=lambda x: x["document_id"]),
        "government_submission": "user_only_not_submitted",
    }
    canonical = json.dumps(package, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":"))
    return {"package": {"data": package, "review_digest": sha256(canonical.encode("utf-8")).hexdigest()}}


def build_preparation_graph():
    graph = StateGraph(PreparationState)
    graph.add_node("evaluate_approved_rules", _rules)
    graph.add_node("validate_confirmed_documents", _documents)
    graph.add_node("prepare_reviewable_package", _package)
    graph.add_edge(START, "evaluate_approved_rules")
    graph.add_edge("evaluate_approved_rules", "validate_confirmed_documents")
    graph.add_edge("validate_confirmed_documents", "prepare_reviewable_package")
    graph.add_edge("prepare_reviewable_package", END)
    return graph.compile()


GRAPH = build_preparation_graph()


def assess_preparation(*, case_id: str, facts: dict, catalog: dict,
                       citation_is_approved, documents: list[dict]) -> dict:
    # Each run has a strict three-node graph, no external tool or recursion.
    result = GRAPH.invoke({
        "case_id": case_id,
        "facts": facts,
        "catalog": catalog,
        "citations_approved": citation_is_approved,
        "documents": documents,
        "blocking_issues": [],
        "package": None,
    })
    return {
        "status": result["status"],
        "rules": result["rule_result"],
        "document_review": result["document_review"],
        "blocking_issues": result["blocking_issues"],
        "package": result.get("package"),
        "next_action": (
            "correct_documents" if result["document_review"]["status"] == "conflict" else
            "review_package" if result["status"] == "reviewable" else
            "correct_documents" if result["status"] == "needs_review" else
            "provide_documents" if result["status"] == "needs_documents" else
            "answer_missing_facts" if result["status"] == "needs_information" else
            "human_review_required"
        ),
    }
