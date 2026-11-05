"""Strict extractive response verification for untrusted model output.

This is deliberately *not* general factual entailment or legal correctness.
It prevents the preview from publishing arbitrary prose with decorative
citations. Every visible line must be an exact quotation copied from the
specific approved and hash-checked passage identified by that line.
"""
import re
import unicodedata
from collections.abc import Mapping

# Enforce a small, unambiguous grammar: [version-id:ordinal] "source quotation"
ID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}:[0-9]{4}"
CLAIM = re.compile(r"^\[(" + ID + r")\] \"([^\"\n]{24,400})\"$")
WHITESPACE = re.compile(r"\s+")


def _normalise(value: str) -> str:
    return WHITESPACE.sub(" ", unicodedata.normalize("NFC", value)).strip()


def verify_exact_quotations(
    output: str, approved_passages: Mapping[str, str],
) -> bool:
    """Accept only 1-4 copied, citation-bound quotes with no extra text.

    Quote-only output disallows generated paraphrases, instructions,
    unsupported inferred claims, commentary and deceptive citations.
    Official material still requires human review for applicability.
    """
    if not isinstance(output, str) or len(output) > 2000:
        return False
    lines = output.splitlines()
    if not 1 <= len(lines) <= 4:
        return False
    seen = set()
    for line in lines:
        claim = CLAIM.fullmatch(line)
        if claim is None:
            return False
        citation, quote = claim.groups()
        passage = approved_passages.get(citation)
        if passage is None:
            return False
        cleaned = _normalise(quote)
        if len(cleaned) < 24 or len(cleaned) > 400:
            return False
        if cleaned not in _normalise(passage):
            return False
        if (citation, cleaned) in seen:
            return False
        seen.add((citation, cleaned))
    return True
