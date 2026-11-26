from __future__ import annotations

import re
from typing import Literal

import langdetect
from langdetect import DetectorFactory, detect_langs

DetectorFactory.seed = 0

_THRESHOLD = 0.80

_ITALIAN_FUNCTION_WORDS = frozenset(
    {"il", "lo", "la", "di", "che", "per", "non", "sono", "come", "una"}
)
_ENGLISH_FUNCTION_WORDS = frozenset({"the", "and", "how", "what", "do", "is", "a", "to"})


def _top_lang(text: str) -> tuple[str, float]:
    results = detect_langs(text)
    top = results[0]
    return top.lang, top.prob


def _word_count_branch(text: str) -> tuple[Literal["en", "it"], bool]:
    words = set(re.findall(r"\b\w+\b", text.lower()))
    italian = len(words & _ITALIAN_FUNCTION_WORDS)
    english = len(words & _ENGLISH_FUNCTION_WORDS)
    if italian > english:
        return ("it", False)
    return ("en", False)


def detect_language(text: str) -> tuple[Literal["en", "it"], bool]:
    try:
        lang, prob = _top_lang(text)
    except langdetect.LangDetectException:
        return _word_count_branch(text)

    if prob >= _THRESHOLD:
        if lang == "en":
            return ("en", False)
        if lang == "it":
            return ("it", False)
        return ("en", True)

    return _word_count_branch(text)