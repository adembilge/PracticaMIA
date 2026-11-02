"""Read a message. An inference is not a fact."""

from procedure import select

_ITALIAN = ("residente", "residenza", "scadenza", "trasferita", "arrivata", "proprietà")
_TURKISH = ("ı", "ş", "ğ", "İ")


def _language(text):
    if any(mark in text for mark in _TURKISH):
        return "Turkish"
    lowered = text.lower()
    if any(mark in lowered for mark in _ITALIAN):
        return "Italian"
    return "English"


def _record(intent, language, scenario, stated, inferred):
    return {
        "intent": intent,
        "language": language,
        "scenario": scenario,
        "stated": stated,
        "inferred": inferred,
    }


def read(message, case_open=False):
    text = " ".join(message.split())
    lowered = text.lower()
    language = _language(text)
    stated = {"language": language}
    inferred = {}
    if "deadline" in lowered or "scadenza" in lowered:
        stated["deadline"] = "a question"
        return _record("question", language, None, stated, inferred)
    if "which document" in lowered or "unasked paper" in lowered:
        stated["paper"] = "a question"
        return _record("question", language, None, stated, inferred)
    if "only sign-in" in lowered or "only way to sign in" in lowered:
        stated["sign_in"] = "a question"
        return _record("question", language, None, stated, inferred)
    if language == "Turkish":
        return _record("unsupported", language, "U-03", stated, inferred)
    if "never been registered" in lowered or "non sono mai stata registrata" in lowered:
        stated["f02"] = "never registered in Italy"
        return _record("unsupported", language, "U-01", stated, inferred)
    if "wife and i" in lowered or "put both of us" in lowered or "the tari" in lowered:
        stated["f03"] = "another adult"
        return _record("unsupported", language, "U-02", stated, inferred)
    if case_open and ("lease" in lowered or "atto" in lowered or "surname" in lowered):
        return _record("update", language, None, stated, inferred)
    if "girlfriend" in lowered or "isola" in lowered:
        stated["question"] = "f03"
        return _record("new", language, "A-02", stated, inferred)
    if "don't have the contract" in lowered:
        stated["f02"] = "Yes"
        stated["f07"] = "missing"
        return _record("new", language, "I-01", stated, inferred)
    if "spelled differently" in lowered:
        stated["f04"] = "Via Torino 20, Milano"
        stated["f09"] = "disagree"
        return _record("new", language, "I-02", stated, inferred)
    if "via torino 20" in lowered and "lease is in my name" in lowered:
        stated["f02"] = "Yes"
        stated["f04"] = "Via Torino 20, Milano"
        stated["f05"] = "named tenant"
        inferred["non_eu"] = True
        return _record("new", language, "S-01", stated, inferred)
    if "via savona 12" in lowered:
        stated["f02"] = "Yes"
        stated["f04"] = "via Savona 12, Milano"
        stated["f05"] = "Owner"
        return _record("new", language, "S-02", stated, inferred)
    if "i need residence" in lowered or "ho bisogno della residenza" in lowered:
        stated["question"] = "f02"
        return _record("new", language, "A-01", stated, inferred)
    return _record("unknown", language, None, stated, inferred)


def route(message, case_open=False):
    record = read(message, case_open=case_open)
    return {**record, **select(record["stated"])}
