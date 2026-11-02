"""One decision from the rule order. A missing fact stays missing."""


def _missing(value):
    return value is None or (isinstance(value, str) and not value.strip())


def _unknown(field):
    return {"id": field, "decision": "unknown", "missing": field}


def _rule(rule_id, decision):
    return {"id": rule_id, "decision": decision}


def evaluate(facts):
    if any(facts.get(key) for key in ("research", "deadline", "paper", "sign_in")):
        return _rule("R-09", "not stated")
    if "language" not in facts or _missing(facts.get("language")):
        return _unknown("language")
    if facts["language"] not in ("English", "Italian"):
        return _rule("R-01", "no case")
    question = facts.get("question")
    if question in ("f02", "f03") and _missing(facts.get(question)):
        if facts.get("asked"):
            return _unknown(question) | {"id": "R-03"}
        return _rule("R-03", "ask once") | {"missing": question}
    if facts.get("door") == "excluded":
        return _rule("R-02", "no case")
    if "f02" in facts and not _missing(facts.get("f02")) and facts.get("f02") != "Yes":
        return _rule("R-04", "no case")
    if (
        "f03" in facts
        and not _missing(facts.get("f03"))
        and facts.get("f03") not in ("Owner, alone", "named tenant, alone")
    ):
        return _rule("R-04", "no case")
    if "f05" in facts and not _missing(facts.get("f05")) and facts.get("f05") not in (
        "Owner",
        "named tenant",
    ):
        return _rule("R-04", "no case")
    if "f04" in facts and not _missing(facts.get("f04")):
        address = facts.get("f04")
        if not isinstance(address, str) or "Milano" not in address:
            return _rule("R-04", "no case")
    if facts.get("non_eu") and "f06" in facts and not _missing(facts.get("f06")) and facts.get("f06") != "Yes":
        return _rule("R-04", "no case")
    if "f04" not in facts or _missing(facts.get("f04")):
        return _unknown("f04")
    if "f05" not in facts or _missing(facts.get("f05")):
        return _unknown("f05")
    if facts.get("non_eu") and ("f06" not in facts or _missing(facts.get("f06"))):
        return _unknown("f06")
    pairs = {"Owner, alone": "Owner", "named tenant, alone": "named tenant"}
    if facts.get("f03") in pairs and pairs[facts["f03"]] != facts["f05"]:
        return _unknown("f05")
    if "f07" not in facts:
        return _rule("R-05", "open")
    if facts.get("f07") in ("missing", "failed", "unreadable"):
        return _rule("R-06", "not ready")
    if facts.get("f07") != "read":
        return _unknown("f07")
    if facts.get("non_eu"):
        if "f08" not in facts or _missing(facts.get("f08")):
            return _unknown("f08")
        if facts.get("f08") in ("missing", "failed", "unreadable"):
            return _rule("f08", "not ready")
        if facts.get("f08") != "read":
            return _unknown("f08")
    if "f09" not in facts or _missing(facts.get("f09")):
        return _unknown("f09")
    if facts.get("f09") in ("disagree", "mismatch") and not facts.get("named"):
        return _rule("R-07", "not ready")
    if facts.get("f09") == "agree" or facts.get("named"):
        return _rule("R-08", "ready")
    return _unknown("f09")
