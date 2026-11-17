"""Candidate matching for reviewed catalogue names; no procedural routing.

The caller supplies versioned catalogue records. This module never imports a
directory, approves an alias, assigns an authority role, or mutates a case.
"""

from dataclasses import dataclass
from typing import Literal
import unicodedata


NameKind = Literal[
    "current_official", "former_official", "official_acronym",
    "reviewed_alias", "search_variant",
]
EntityType = Literal["authority", "municipality", "province", "region"]
MatchStatus = Literal["resolved", "ambiguous", "needs_confirmation", "unresolved"]

_KIND_RANK = {
    "current_official": 0,
    "former_official": 1,
    "official_acronym": 2,
    "reviewed_alias": 3,
    "search_variant": 4,
}


@dataclass(frozen=True)
class CatalogueName:
    catalogue_id: str
    entity_type: EntityType
    display_name: str
    name: str
    kind: NameKind
    evidence_ref: str
    location_ids: tuple[str, ...] = ()
    language: str | None = None
    approved_for_search: bool = False


@dataclass(frozen=True)
class NameCandidate:
    catalogue_id: str
    entity_type: EntityType
    display_name: str
    matched_name: str
    matched_kind: NameKind
    evidence_ref: str
    location_ids: tuple[str, ...]
    match_type: Literal["exact", "spelling_suggestion"]


@dataclass(frozen=True)
class NameMatchResult:
    status: MatchStatus
    candidates: tuple[NameCandidate, ...]
    selected_id: str | None = None
    selected_type: EntityType | None = None
    distinguishing_field: Literal["location_or_type"] | None = None


def normalize_name(value: str) -> str:
    """Build an accent-insensitive key without deleting words or numbers."""
    folded = unicodedata.normalize("NFKD", value.casefold())
    characters = [
        character for character in folded
        if not unicodedata.combining(character)
    ]
    return " ".join("".join(
        character if character.isalnum() else " " for character in characters
    ).split())


def _spelling_suggestion(query: str, name: str) -> bool:
    # Offer only a single insertion, deletion, substitution or transposition.
    # Broad similarity over shared authority prefixes produces many false hits.
    if min(len(query), len(name)) < 5 or abs(len(query) - len(name)) > 1:
        return False
    if len(query) == len(name):
        differences = [i for i, (a, b) in enumerate(zip(query, name)) if a != b]
        if len(differences) == 1:
            return True
        return (
            len(differences) == 2
            and differences[1] == differences[0] + 1
            and query[differences[0]] == name[differences[1]]
            and query[differences[1]] == name[differences[0]]
        )
    shorter, longer = sorted((query, name), key=len)
    i = j = skipped = 0
    while i < len(shorter) and j < len(longer):
        if shorter[i] == longer[j]:
            i += 1
            j += 1
        else:
            skipped += 1
            j += 1
            if skipped > 1:
                return False
    return True


def match_catalogue_names(
    query: str,
    names: tuple[CatalogueName, ...] | list[CatalogueName],
    *,
    confirmed_location_id: str | None = None,
    entity_type: EntityType | None = None,
) -> NameMatchResult:
    """Return every plausible ID; only exact, context-unique names resolve.

    `confirmed_location_id` must come from a user-confirmed case fact, not an
    IP address or office address. The selected ID is an identity match only.
    """
    if len(query) > 180:
        raise ValueError("Name query must be at most 180 characters")
    key = normalize_name(query)
    if not key:
        raise ValueError("Name query must contain letters or numbers")

    best: dict[tuple[EntityType, str], tuple[tuple[int, int], NameCandidate]] = {}
    for record in names:
        if not record.approved_for_search or not record.evidence_ref.strip():
            continue
        if entity_type is not None and record.entity_type != entity_type:
            continue
        name_key = normalize_name(record.name)
        acronym_match = (
            record.kind == "official_acronym"
            and name_key.replace(" ", "") == key.replace(" ", "")
        )
        if name_key == key or acronym_match:
            match_type: Literal["exact", "spelling_suggestion"] = "exact"
            rank = (0, _KIND_RANK[record.kind])
        elif record.kind != "official_acronym" and _spelling_suggestion(key, name_key):
            match_type = "spelling_suggestion"
            rank = (1, _KIND_RANK[record.kind])
        else:
            continue
        candidate = NameCandidate(
            catalogue_id=record.catalogue_id,
            entity_type=record.entity_type,
            display_name=record.display_name,
            matched_name=record.name,
            matched_kind=record.kind,
            evidence_ref=record.evidence_ref,
            location_ids=record.location_ids,
            match_type=match_type,
        )
        identity = (record.entity_type, record.catalogue_id)
        existing = best.get(identity)
        if existing is None or rank < existing[0]:
            best[identity] = rank, candidate

    ordered = tuple(
        item[1] for item in sorted(
            best.values(), key=lambda item: (
                item[0], item[1].display_name.casefold(), item[1].catalogue_id,
            )
        )
    )
    if not ordered:
        return NameMatchResult(status="unresolved", candidates=())

    eligible = ordered
    if confirmed_location_id is not None:
        eligible = tuple(
            candidate for candidate in ordered
            if confirmed_location_id in candidate.location_ids
        )
        if not eligible:
            return NameMatchResult(status="unresolved", candidates=ordered)

    if len(eligible) > 1:
        return NameMatchResult(
            status="ambiguous", candidates=ordered,
            distinguishing_field="location_or_type",
        )
    only = eligible[0]
    if only.match_type == "spelling_suggestion" or (
        only.matched_kind == "official_acronym"
        and confirmed_location_id is None
        and entity_type is None
    ):
        return NameMatchResult(status="needs_confirmation", candidates=ordered)
    return NameMatchResult(
        status="resolved", candidates=ordered, selected_id=only.catalogue_id,
        selected_type=only.entity_type,
    )
