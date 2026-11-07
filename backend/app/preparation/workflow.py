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


class PreparationState(TypedDict, total=False):
    case_id: str
    facts: dict
    catalog: dict
    citations_approved: Any
    documents: list[dict]
    rule_result: dict
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
    issues = list(state["blocking_issues"])
    if rule["decision"] != "supported":
        return {"status": rule["decision"], "blocking_issues": issues}
    documents = state.get("documents", [])
    required = set(rule["required_document_types"])
    approved_types: set[str] = set()
    for doc in documents:
        if doc.get("status") == "confirmed":
            approved_types.add(doc.get("document_type", ""))
        elif doc.get("status") == "unreadable":
            issues.append("document_unreadable")
        for field, value in doc.get("confirmed_fields", {}).items():
            if (field in state["facts"]
                and isinstance(value, str)
                and str(state["facts"][field]).strip().casefold() != value.strip().casefold()):
                issues.append(f"document_conflict:{field}")
    for category in sorted(required - approved_types):
        issues.append(f"missing_document:{category}")
    return {
        "status": "needs_review" if any(s.startswith("document_conflict:")
                                            for s in issues) else
                  "needs_documents" if issues else "reviewable",
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
        "blocking_issues": result["blocking_issues"],
        "package": result.get("package"),
        "next_action": (
            "review_package" if result["status"] == "reviewable" else
            "correct_documents" if result["status"] == "needs_review" else
            "provide_documents" if result["status"] == "needs_documents" else
            "answer_missing_facts" if result["status"] == "needs_information" else
            "human_review_required"
        ),
    }
