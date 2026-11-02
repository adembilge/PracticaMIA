"""One type from the page text. No proposal can assign it."""
from extract import read

MARKERS = (
    ("lease", ("lease", "contratto di locazione")),
    ("ownership", ("ownership", "atto di proprieta")),
    ("identity", ("passport", "passaporto", "identity card", "carta d'identita")),
    ("permit", ("permesso di soggiorno", "residence permit")),
)


def _has(text, phrase):
    return (" " + phrase + " ") in (" " + text.replace("\n", " ") + " ")


def classify(payload):
    found = read(payload)
    text = "\n".join(page["text"] for page in found["pages"]).lower()
    if not text.strip():
        return {"type": "unknown"}
    hits = [name for name, words in MARKERS if any(_has(text, word) for word in words)]
    if len(hits) == 1:
        return {"type": hits[0]}
    if len(hits) > 1:
        return {"type": "ambiguous"}
    return {"type": "unknown"}
