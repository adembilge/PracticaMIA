"""One procedure, or none. A missing fact is not a guess."""

from rules import evaluate

PROCEDURE = "address change"
ABROAD = "Comune di Milano service for foreigners arriving from abroad"
ANPR = "ANPR"
OUT = "not in this release"
QUESTURA = "Questura"
LANGUAGES = ("English", "Italian")
ALONE = ("Owner, alone", "named tenant, alone")
TITLES = ("Owner", "named tenant")


def _present(facts, key):
    value = facts.get(key)
    return key in facts and value is not None and not (isinstance(value, str) and not value.strip())


def _door(facts):
    if facts.get("language") not in LANGUAGES:
        return "English or Italian"
    if facts.get("door") == "excluded":
        return None
    if _present(facts, "f02") and facts["f02"] != "Yes":
        if facts["f02"] == "never registered in Italy":
            return ABROAD
        if facts["f02"] == "registered in another municipality":
            return ANPR
        return None
    if _present(facts, "f03") and facts["f03"] not in ALONE:
        if facts["f03"] == "another adult":
            return ANPR
        return OUT
    if _present(facts, "f05") and facts["f05"] not in TITLES:
        return OUT
    address = facts.get("f04")
    if _present(facts, "f04") and (not isinstance(address, str) or "Milano" not in address):
        return None
    if facts.get("non_eu") and facts.get("f06") == "No":
        return QUESTURA
    return None


def select(facts):
    result = dict(evaluate(facts))
    if result["decision"] in ("open", "not ready", "ready"):
        result["procedure"] = PROCEDURE
        return result
    result["procedure"] = None
    if result["decision"] == "no case":
        door = _door(facts)
        if door:
            result["door"] = door
    return result
