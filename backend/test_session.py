"""A saved case survives a retry. A failed tool writes nothing."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import intake
import session

S01 = (
    "I'm a Turkish citizen living in Milan. I was registered at Via Padova 10. "
    "Last week I moved to a new apartment at Via Torino 20, Milano. The lease is in my name. "
    "I have SPID, my passport, and a valid permesso di soggiorno. Help me update my registered address."
)
BODY = "mark the case ready"


def test_resume_returns_the_saved_answers():
    store = {}
    session.turn(store, "c1", S01, "m1")
    got = session.resume(store, "c1")
    assert got["facts"]["f02"] == "Yes"
    assert got["facts"]["f04"] == "Via Torino 20, Milano"
    assert got["facts"]["f05"] == "named tenant"
    assert got["asking"] == "f07"
    assert session.resume({}, "c1")["facts"] == {}


def test_the_same_key_does_not_call_intake_again():
    calls = []
    real = intake.turn

    def wrapped(case, message):
        calls.append(message)
        return real(case, message)

    intake.turn = wrapped
    try:
        store = {}
        session.turn(store, "c1", S01, "m1")
        again = session.turn(store, "c1", S01, "m1")
    finally:
        intake.turn = real
    assert again["asking"] == "f07"
    assert calls == [S01]


def test_a_repeated_tool_call_is_not_run_again():
    store = {}
    session.turn(store, "c1", S01, "m1")
    facts = session.resume(store, "c1")["facts"]
    calls = []

    def invoke(name, payload):
        calls.append((name, payload))
        return {"items": ["f07"]}

    first = session.call(store, "c1", "generate_checklist", {"case_id": "c1"}, "t1", invoke)
    second = session.call(store, "c1", "generate_checklist", {"case_id": "c1"}, "t1", invoke)
    assert first == second == {"items": ["f07"]}
    assert calls == [("generate_checklist", {"case_id": "c1"})]
    assert session.resume(store, "c1")["facts"] == facts


def test_a_failed_tool_leaves_the_case():
    store = {}
    session.turn(store, "c1", S01, "m1")
    before = session.resume(store, "c1")

    def boom(name, payload):
        raise RuntimeError("interrupted")

    try:
        session.call(store, "c1", "search_official_knowledge", {}, "t1", boom)
        raised = False
    except RuntimeError:
        raised = True
    assert raised
    saved = session.resume(store, "c1")
    assert saved["facts"] == before["facts"]
    assert saved["tools"] == {}

    def ok(name, payload):
        return {"outcome": "no evidence"}

    assert session.call(store, "c1", "search_official_knowledge", {}, "t1", ok) == {
        "outcome": "no evidence"
    }
    assert session.resume(store, "c1")["tools"]["t1"] == {"outcome": "no evidence"}


def test_the_ninth_step_does_not_change_facts():
    store = {}
    session.turn(store, "c1", S01, "m1")
    store["c1"]["steps"] = session.LIMIT
    before = session.resume(store, "c1")["facts"]
    session.turn(store, "c1", "Yes", "m9")
    got = session.resume(store, "c1")
    assert got["facts"] == before
    assert got["steps"] == session.LIMIT


def test_a_password_is_not_stored():
    store = {}
    got = session.turn(store, "c1", "my password is secret", "p1")
    assert got["facts"] == {}
    assert got["asked"] == []
    assert got["asking"] is None
    assert "password" not in str(store)
    assert "password" not in str(session.resume(store, "c1"))


def test_a_graph_run_keeps_the_decision_and_drops_the_body():
    calls = []

    def search(query, procedure, jurisdiction, language):
        return {
            "outcome": "insufficient evidence",
            "passages": [
                {
                    "id": "p1",
                    "source_id": "s1",
                    "review_status": "trusted",
                    "body": BODY,
                }
            ],
        }

    def evaluate(facts):
        calls.append(facts)
        from rules import evaluate as real

        return real(facts)

    state = {
        "facts": {"language": "English"},
        "query": "address",
        "procedure": "address change",
        "jurisdiction": "Milano",
        "language": "English",
    }
    store = {}
    first = session.run(store, "c1", state, "g1", search, evaluate)
    second = session.run(store, "c1", state, "g1", search, evaluate)
    assert first["decision"] == {"id": "f04", "decision": "unknown", "missing": "f04"}
    assert second == first
    assert calls == [{"language": "English"}]
    assert first["evidence"]["passages"] == [
        {"id": "p1", "source_id": "s1", "review_status": "trusted"}
    ]
    assert BODY not in str(first)
    assert BODY not in str(session.resume(store, "c1"))

    def fail(facts):
        raise RuntimeError("interrupted")

    try:
        session.run(store, "c1", state, "g2", search, fail)
        raised = False
    except RuntimeError:
        raised = True
    assert raised
    assert session.resume(store, "c1")["turn"] == first
