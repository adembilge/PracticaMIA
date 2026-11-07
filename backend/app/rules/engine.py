"""Pure, deny-by-default three-valued eligibility and checklist engine.

Never infer Italian law from a model. A catalog is usable only if its version,
reviewer identity, coverage declaration, and EVERY rule citation are confirmed
against the existing approval-gated source registry at evaluation time.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal
import json
import re

Truth = Literal["TRUE", "FALSE", "UNKNOWN"]
_FIELD = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_CODE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
MAX_DEPTH = 6
MAX_NODES = 48
MAX_RULES = 60
MAX_FACTS = 48
PROCEDURE = "milan_residence_change"
JURISDICTION = "IT-MI-MILANO"


class InvalidCatalog(ValueError):
    pass


@dataclass(frozen=True)
class RuleResult:
    decision: str
    ruleset_version: str | None
    applicable_rule_ids: tuple[str, ...]
    missing_fields: tuple[str, ...]
    required_document_types: tuple[str, ...]
    checklist: tuple[dict, ...]
    evidence_refs: tuple[str, ...]
    blocking_issues: tuple[str, ...]
    demo_only: bool = False

    def as_dict(self) -> dict:
        return {
            "decision": self.decision,
            "ruleset_version": self.ruleset_version,
            "applicable_rule_ids": list(self.applicable_rule_ids),
            "missing_fields": list(self.missing_fields),
            "required_document_types": list(self.required_document_types),
            "checklist": list(self.checklist),
            "evidence_refs": list(self.evidence_refs),
            "blocking_issues": list(self.blocking_issues),
            "demo_only": self.demo_only,
        }


def evaluate_condition(node: dict, facts: dict, *, depth: int = 0,
                       budget: list[int] | None = None) -> tuple[Truth, set[str]]:
    if budget is None:
        budget = [MAX_NODES]
    budget[0] -= 1
    if budget[0] < 0 or depth > MAX_DEPTH or not isinstance(node, dict):
        raise InvalidCatalog("Condition complexity exceeded")
    types = {"all", "any", "not", "field"}
    if len(types & set(node)) != 1:
        raise InvalidCatalog("Condition must have exactly one operator")
    if "all" in node or "any" in node:
        operator = "all" if "all" in node else "any"
        if set(node) != {operator}:
            raise InvalidCatalog("Unsupported condition keys")
        children = node[operator]
        if not isinstance(children, list) or not 1 <= len(children) <= 12:
            raise InvalidCatalog("Condition group needs 1-12 children")
        children_results = [
            evaluate_condition(item, facts, depth=depth + 1, budget=budget)
            for item in children
        ]
        values = [item[0] for item in children_results]
        if operator == "all":
            value = "FALSE" if "FALSE" in values else ("UNKNOWN" if "UNKNOWN" in values else "TRUE")
        else:
            value = "TRUE" if "TRUE" in values else ("UNKNOWN" if "UNKNOWN" in values else "FALSE")
        # A known short-circuit outcome needs no further fields.
        missing = set().union(*(r[1] for r in children_results)) if value == "UNKNOWN" else set()
        return value, missing
    if "not" in node:
        if set(node) != {"not"}:
            raise InvalidCatalog("Unsupported condition keys")
        value, missing = evaluate_condition(
            node["not"], facts, depth=depth + 1, budget=budget,
        )
        return {"TRUE": "FALSE", "FALSE": "TRUE", "UNKNOWN": "UNKNOWN"}[value], missing
    if not {"field", "operator"}.issubset(node) or not set(node).issubset(
        {"field", "operator", "value"}
    ):
        raise InvalidCatalog("Malformed comparison")
    field, operator = node["field"], node["operator"]
    if not isinstance(field, str) or not _FIELD.fullmatch(field):
        raise InvalidCatalog("Invalid field identifier")
    if operator not in {"equals", "in", "exists"}:
        raise InvalidCatalog("Unsupported comparison operator")
    if operator == "exists":
        if "value" in node:
            raise InvalidCatalog("Exists comparison has no value")
        return ("TRUE" if field in facts and facts[field] is not None else "FALSE"), set()
    if field not in facts or facts[field] is None or facts[field] == "":
        return "UNKNOWN", {field}
    actual = facts[field]
    if type(actual) not in (str, int, bool) or (
        isinstance(actual, str) and len(actual) > 250
    ):
        raise ValueError("Facts must contain bounded scalar values")
    if operator == "equals":
        if type(node.get("value")) not in (str, int, bool):
            raise InvalidCatalog("Equals needs a scalar value")
        return ("TRUE" if type(actual) is type(node["value"]) and actual == node["value"] else "FALSE"), set()
    expected = node.get("value")
    if (not isinstance(expected, list) or not 1 <= len(expected) <= 16
            or any(type(x) not in (str, int, bool) for x in expected)):
        raise InvalidCatalog("In comparison needs 1-16 scalar values")
    return ("TRUE" if any(type(actual) is type(x) and actual == x for x in expected) else "FALSE"), set()


def load_catalog(serialized: str) -> dict:
    """Reject invalid/truncated, non-object, oversized or duplicate-key JSON."""
    if len(serialized) > 80000:
        raise InvalidCatalog("Catalog exceeds size budget")

    def no_duplicate_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise InvalidCatalog("Duplicate catalog key")
            result[key] = value
        return result

    try:
        data = json.loads(serialized, object_pairs_hook=no_duplicate_keys)
    except (ValueError, TypeError) as exc:
        raise InvalidCatalog("Invalid catalog JSON") from exc
    if not isinstance(data, dict):
        raise InvalidCatalog("Catalog must be an object")
    return data


def _check_rule(rule: dict) -> None:
    if not isinstance(rule, dict):
        raise InvalidCatalog("Invalid rule")
    if set(rule) != {"id", "kind", "status", "condition", "result", "evidence_refs"}:
        raise InvalidCatalog("Rule keys do not match contract")
    if not isinstance(rule["id"], str) or not _CODE.fullmatch(rule["id"]):
        raise InvalidCatalog("Invalid rule ID")
    if rule["kind"] not in ("route", "requirement") or rule["status"] != "active":
        raise InvalidCatalog("Only active route/requirement rules are allowed")
    refs = rule["evidence_refs"]
    if (not isinstance(refs, list) or not 1 <= len(refs) <= 12
            or any(not isinstance(x, str) or len(x) > 96 or not x for x in refs)
            or len(set(refs)) != len(refs)):
        raise InvalidCatalog("Each active rule requires unique evidence citations")
    result = rule["result"]
    if not isinstance(result, dict):
        raise InvalidCatalog("Missing rule result")
    if rule["kind"] == "route":
        if result != {"route": "supported_individual"}:
            raise InvalidCatalog("Unknown route result")
    else:
        if set(result) != {"description", "required_document_types"}:
            raise InvalidCatalog("Invalid requirement result")
        if not isinstance(result["description"], str) or not 1 <= len(result["description"]) <= 240:
            raise InvalidCatalog("Invalid requirement description")
        documents = result["required_document_types"]
        if (not isinstance(documents, list) or len(documents) > 12
                or any(not isinstance(x, str) or not _CODE.fullmatch(x) for x in documents)):
            raise InvalidCatalog("Invalid document category")


def evaluate_rules(
    catalog: dict, confirmed_facts: dict,
    evidence_is_approved: Callable[[str], bool], *,
    demo_only: bool = False,
) -> RuleResult:
    """Evaluation has no writes, LLM calls, or external submission side effects."""
    version = catalog.get("version") if isinstance(catalog, dict) else None

    def blocked(code: str) -> RuleResult:
        return RuleResult("blocked", version if isinstance(version, str) else None,
                          (), (), (), (), (), (code,), demo_only)

    if (not isinstance(catalog, dict) or catalog.get("status") != "active"
            or catalog.get("jurisdiction") != JURISDICTION
            or catalog.get("procedure_id") != PROCEDURE
            or not isinstance(version, str) or not 1 <= len(version) <= 80
            or not isinstance(catalog.get("approved_by"), str)
            or not catalog["approved_by"].strip()
            or not isinstance(catalog.get("approved_at"), str)
            or not catalog["approved_at"].strip()
            or catalog.get("complete_scenario_coverage") is not True):
        return blocked("ruleset_not_human_approved")
    rules = catalog.get("rules")
    if not isinstance(rules, list) or not 1 <= len(rules) <= MAX_RULES:
        return blocked("ruleset_incomplete")
    if (not isinstance(confirmed_facts, dict) or len(confirmed_facts) > MAX_FACTS
            or any(not isinstance(key, str) or not _FIELD.fullmatch(key)
                   for key in confirmed_facts)):
        raise ValueError("Invalid confirmed facts")

    seen: set[str] = set()
    all_refs: list[str] = []
    try:
        for rule in rules:
            _check_rule(rule)
            if rule["id"] in seen:
                raise InvalidCatalog("Duplicate rule IDs")
            seen.add(rule["id"])
            # Validate even non-applicable rules: a stale rule cannot produce
            # a misleading statement that the ruleset is complete.
            evaluate_condition(rule["condition"], {})
            all_refs.extend(rule["evidence_refs"])
    except InvalidCatalog:
        return blocked("invalid_ruleset")
    if not any(rule["kind"] == "route" for rule in rules):
        return blocked("missing_route_rule")

    # Fail closed on every source citation, not just one matching condition.
    try:
        citations_ok = all(evidence_is_approved(ref) for ref in set(all_refs))
    except Exception:
        citations_ok = False
    if not citations_ok:
        return blocked("source_unapproved_revoked_or_stale")

    applicable: list[str] = []
    missing: set[str] = set()
    docs: set[str] = set()
    checklist: list[dict] = []
    refs: set[str] = set()
    route_true = False
    route_unknown = False
    for rule in rules:
        outcome, needed = evaluate_condition(rule["condition"], confirmed_facts)
        if rule["kind"] == "route":
            route_true |= outcome == "TRUE"
            route_unknown |= outcome == "UNKNOWN"
        if outcome == "UNKNOWN":
            missing.update(needed)
        if outcome != "TRUE":
            continue
        applicable.append(rule["id"])
        refs.update(rule["evidence_refs"])
        if rule["kind"] == "requirement":
            docs.update(rule["result"]["required_document_types"])
            checklist.append({
                "rule_id": rule["id"],
                "description": rule["result"]["description"],
                "required_document_types": rule["result"]["required_document_types"],
                "evidence_refs": rule["evidence_refs"],
            })

    if route_unknown and not route_true:
        decision = "needs_information"
    elif not route_true:
        decision = "unsupported"
    elif missing:
        decision = "needs_information"
    else:
        decision = "supported"
    return RuleResult(
        decision, version, tuple(applicable), tuple(sorted(missing)),
        tuple(sorted(docs)), tuple(checklist), tuple(sorted(refs)),
        ("confirm_missing_facts",) if decision == "needs_information" else
        ("route_not_supported",) if decision == "unsupported" else (),
        demo_only,
    )
