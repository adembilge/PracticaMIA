"""One question per turn. A stored fact is not asked again."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from intake import blank, turn

S01 = (
    "I'm a Turkish citizen living in Milan. I was registered at Via Padova 10. "
    "Last week I moved to a new apartment at Via Torino 20, Milano. The lease is in my name. "
    "I have SPID, my passport, and a valid permesso di soggiorno. Help me update my registered address."
)
S02 = (
    "Sono residente a Milano in via Solari 4. Ho comprato un appartamento in via Savona 12, "
    "sempre a Milano, e ci abito da dieci giorni. Ho la CIE e l'atto di proprietà. "
    "Devo aggiornare la residenza, solo per me."
)
I01 = (
    "I live in Milan and I moved to a new place in Milan. I need to change my residence. "
    "I have my passport and my permesso. I don't have the contract on my phone."
)
A01 = "I moved to Milan last month. I need residence."
U01 = (
    "I landed in Milan two weeks ago from Ankara. I have never been registered in Italy. "
    "I rented a room and need my first residence."
)


def test_s01_asks_for_the_title_paper_once():
    case = turn(blank(), S01)
    assert case["facts"]["f02"] == "Yes"
    assert case["facts"]["f04"] == "Via Torino 20, Milano"
    assert case["facts"]["f05"] == "named tenant"
    assert "non_eu" not in case["facts"]
    assert case["asking"] == "f07"
    assert case["asking"] != "f02"
    again = turn(case, S01)
    assert again["asking"] is None
    assert again["facts"]["f02"] == "Yes"
    assert again.get("stop") != "ready"


def test_s02_asks_for_the_title_paper_and_not_the_identity_paper():
    case = turn(blank(), S02)
    assert case["asking"] == "f07"
    assert "f08" not in case["facts"]
    assert case["asking"] != "f08"


def test_a01_stores_yes_and_does_not_ask_f02_again():
    case = turn(blank(), A01)
    assert case["asking"] == "f02"
    assert "f02" not in case["facts"]
    case = turn(case, "Yes")
    assert case["facts"]["f02"] == "Yes"
    assert case["asking"] == "f04"
    case = turn(case, A01)
    assert case["asking"] != "f02"
    assert case["facts"]["f02"] == "Yes"


def test_i01_does_not_store_a_missing_street_and_then_pauses():
    case = turn(blank(), I01)
    assert case["asking"] == "f04"
    case = turn(case, "I don't have it yet")
    assert "f04" not in case["facts"]
    assert case["asking"] is None
    case = turn(case, "I don't have it yet")
    assert case["asking"] is None
    assert "f04" not in case["facts"]


def test_a_disagreement_pauses_without_choosing_a_name():
    case = {
        "facts": {
            "language": "English",
            "f04": "Via Torino 20, Milano",
            "f05": "named tenant",
            "f07": "read",
            "f09": "disagree",
        },
        "asked": [],
        "asking": None,
    }
    case = turn(case, "I'm not sure")
    assert case["asking"] is None
    assert "name" not in case["facts"]
    assert case["facts"]["f09"] == "disagree"
    assert case.get("stop") != "ready"


def test_a_deadline_leaves_the_stored_facts():
    case = turn(blank(), S01)
    facts = dict(case["facts"])
    case = {"facts": facts, "asked": [], "asking": None}
    case = turn(case, "What is the deadline?")
    assert case["facts"] == facts
    assert case["asking"] is None


def test_u01_asks_nothing_further_and_is_not_ready():
    case = turn(blank(), U01)
    assert case["asking"] is None
    assert case.get("stop") != "ready"


def test_a_password_is_not_stored():
    case = turn(blank(), "my password is secret")
    assert case["facts"] == {}
    assert "password" not in case
    assert case["asking"] is None
