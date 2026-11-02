"""Reference requests. An inference is not a confirmed fact."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from intent import route

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
I02 = (
    "Here is my lease for Via Torino 20 and my permesso. Please finish my Milan address change. "
    "My permesso has my old address, Via Padova 10, and the surname on the lease is spelled "
    "differently from the passport."
)
A01 = "I moved to Milan last month. I need residence."
A01_SHORT = "I need residence in Milan."
A01_IT = "Mi sono trasferita a Milano il mese scorso. Ho bisogno della residenza."
A02 = "I moved in with my girlfriend in Isola. The apartment is in Milan. Can you do my residence?"
U01 = (
    "I landed in Milan two weeks ago from Ankara. I have never been registered in Italy. "
    "I rented a room and need my first residence."
)
U01_IT = "Sono arrivata da Ankara e non sono mai stata registrata in Italia."
U02 = (
    "My wife and I both moved from our old Milan apartment to a new one. "
    "Put both of us on the declaration, file it with my SPID, and update our permessi and the TARI."
)
U03 = "Milano'da yeni bir daireye taşındım. İkamet adresimi güncellemem gerekiyor."
ABROAD = "Comune di Milano service for foreigners arriving from abroad"

ROWS = [
    {
        "name": "S-01",
        "message": S01,
        "intent": "new",
        "language": "English",
        "scenario": "S-01",
        "stated": {
            "language": "English",
            "f02": "Yes",
            "f04": "Via Torino 20, Milano",
            "f05": "named tenant",
        },
        "inferred": {"non_eu": True},
        "id": "R-05",
        "decision": "open",
        "procedure": "address change",
    },
    {
        "name": "S-02",
        "message": S02,
        "intent": "new",
        "language": "Italian",
        "scenario": "S-02",
        "stated": {
            "language": "Italian",
            "f02": "Yes",
            "f04": "via Savona 12, Milano",
            "f05": "Owner",
        },
        "inferred": {},
        "id": "R-05",
        "decision": "open",
        "procedure": "address change",
    },
    {
        "name": "I-01",
        "message": I01,
        "intent": "new",
        "language": "English",
        "scenario": "I-01",
        "stated": {"language": "English", "f02": "Yes", "f07": "missing"},
        "inferred": {},
        "id": "f04",
        "decision": "unknown",
        "missing": "f04",
        "procedure": None,
    },
    {
        "name": "I-02",
        "message": I02,
        "intent": "new",
        "language": "English",
        "scenario": "I-02",
        "stated": {
            "language": "English",
            "f04": "Via Torino 20, Milano",
            "f09": "disagree",
        },
        "inferred": {},
        "id": "f05",
        "decision": "unknown",
        "missing": "f05",
        "procedure": None,
    },
    {
        "name": "A-01",
        "message": A01,
        "intent": "new",
        "language": "English",
        "scenario": "A-01",
        "stated": {"language": "English", "question": "f02"},
        "inferred": {},
        "id": "R-03",
        "decision": "ask once",
        "missing": "f02",
        "procedure": None,
    },
    {
        "name": "A-01 short",
        "message": A01_SHORT,
        "intent": "new",
        "language": "English",
        "scenario": "A-01",
        "stated": {"language": "English", "question": "f02"},
        "inferred": {},
        "id": "R-03",
        "decision": "ask once",
        "missing": "f02",
        "procedure": None,
    },
    {
        "name": "A-01 Italian",
        "message": A01_IT,
        "intent": "new",
        "language": "Italian",
        "scenario": "A-01",
        "stated": {"language": "Italian", "question": "f02"},
        "inferred": {},
        "id": "R-03",
        "decision": "ask once",
        "missing": "f02",
        "procedure": None,
    },
    {
        "name": "A-02",
        "message": A02,
        "intent": "new",
        "language": "English",
        "scenario": "A-02",
        "stated": {"language": "English", "question": "f03"},
        "inferred": {},
        "id": "R-03",
        "decision": "ask once",
        "missing": "f03",
        "procedure": None,
    },
    {
        "name": "U-01",
        "message": U01,
        "intent": "unsupported",
        "language": "English",
        "scenario": "U-01",
        "stated": {"language": "English", "f02": "never registered in Italy"},
        "inferred": {},
        "id": "R-04",
        "decision": "no case",
        "procedure": None,
        "door": ABROAD,
    },
    {
        "name": "U-01 Italian",
        "message": U01_IT,
        "intent": "unsupported",
        "language": "Italian",
        "scenario": "U-01",
        "stated": {"language": "Italian", "f02": "never registered in Italy"},
        "inferred": {},
        "id": "R-04",
        "decision": "no case",
        "procedure": None,
        "door": ABROAD,
    },
    {
        "name": "U-02",
        "message": U02,
        "intent": "unsupported",
        "language": "English",
        "scenario": "U-02",
        "stated": {"language": "English", "f03": "another adult"},
        "inferred": {},
        "id": "R-04",
        "decision": "no case",
        "procedure": None,
        "door": "ANPR",
    },
    {
        "name": "U-03",
        "message": U03,
        "intent": "unsupported",
        "language": "Turkish",
        "scenario": "U-03",
        "stated": {"language": "Turkish"},
        "inferred": {},
        "id": "R-01",
        "decision": "no case",
        "procedure": None,
        "door": "English or Italian",
    },
    {
        "name": "deadline",
        "message": "What is the deadline?",
        "intent": "question",
        "language": "English",
        "scenario": None,
        "stated": {"language": "English", "deadline": "a question"},
        "inferred": {},
        "id": "R-09",
        "decision": "not stated",
        "procedure": None,
    },
    {
        "name": "scadenza",
        "message": "Qual è la scadenza?",
        "intent": "question",
        "language": "Italian",
        "scenario": None,
        "stated": {"language": "Italian", "deadline": "a question"},
        "inferred": {},
        "id": "R-09",
        "decision": "not stated",
        "procedure": None,
    },
    {
        "name": "lease on an open case",
        "message": "Here is the lease.",
        "case_open": True,
        "intent": "update",
        "language": "English",
        "scenario": None,
        "stated": {"language": "English"},
        "inferred": {},
        "id": "f04",
        "decision": "unknown",
        "missing": "f04",
        "procedure": None,
    },
    {
        "name": "lease without a case",
        "message": "Here is the lease.",
        "intent": "unknown",
        "language": "English",
        "scenario": None,
        "stated": {"language": "English"},
        "inferred": {},
        "id": "f04",
        "decision": "unknown",
        "missing": "f04",
        "procedure": None,
    },
]


def test_dataset_routes_every_reference_request():
    for row in ROWS:
        got = route(row["message"], case_open=row.get("case_open", False))
        assert got["intent"] == row["intent"], row["name"]
        assert got["language"] == row["language"], row["name"]
        assert got["scenario"] == row["scenario"], row["name"]
        assert got["stated"] == row["stated"], row["name"]
        assert got["inferred"] == row["inferred"], row["name"]
        assert set(got["inferred"]).isdisjoint(got["stated"]), row["name"]
        assert "password" not in got["stated"], row["name"]
        assert "password" not in got["inferred"], row["name"]
        assert got["id"] == row["id"], row["name"]
        assert got["decision"] == row["decision"], row["name"]
        assert got["procedure"] == row["procedure"], row["name"]
        if "missing" in row:
            assert got["missing"] == row["missing"], row["name"]
        if "door" in row:
            assert got["door"] == row["door"], row["name"]
        assert got["stated"].get("f07") != "read", row["name"]
        assert got["stated"].get("f09") != "agree", row["name"]
