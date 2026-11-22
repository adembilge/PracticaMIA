# Phase 3.9 — Authority and place name matching

[PracticaMIA 2.0 task 22.3](phase-03-official-sources-and-catalog.md#22-import-italian-authority-and-geography-identifiers) resolves a user's name to candidate [stable catalogue IDs](phase-03-stable-entity-ids.md). It covers official and former names, acronyms, language variants and spelling variants. A match identifies a body or territorial unit; it does not prove that the body performs a procedure or serves a particular address.

## Names and provenance

Store each searchable name against one catalogue ID with its entity type, language when known, name kind (`current_official`, `former_official`, `official_acronym`, `reviewed_alias` or `search_variant`), source/batch or reviewer evidence, and any known validity dates. Preserve the original spelling and accents. An [IPA or dated Istat](phase-03-official-identifiers.md) import can establish names present in that batch; an inferred translation, user wording or fuzzy spelling cannot become an official name merely because it matches. Keep former names searchable after a rename without changing historical case links. A disputed or unverified alias stays out of trusted matching until reviewed.

Generate a separate search key for case folding, Unicode normalization, whitespace and punctuation handling, and accent-insensitive lookup. Retain the stored name untouched. Do not strip entity-type words, municipality/province qualifiers or numbers in a way that makes two distinct bodies identical. Language and spelling expansion should be explicit, versioned and testable; an English paraphrase is a reviewed alias or query expansion, not a replacement for the Italian official name.

## Candidate resolution

1. Search current official names and exact external codes first, then former names and official acronyms, then reviewed aliases and conservative spelling variants. Return catalogue IDs with display name, entity type, matched name kind, location context, and match explanation. A code is interpreted in its source namespace and reference date; an unqualified string that could be several code types remains ambiguous.
2. Preserve all plausible candidates that share a name or normalized key. Ranking may use name quality and confirmed context, but it must not hide a relevant namesake. A fuzzy hit or acronym alone never authorizes a case link.
3. If the request and confirmed case context leave one candidate, resolve to that ID. If multiple candidates remain, show them and ask the smallest distinguishing question, ordinarily municipality, province/region or authority type. Do not infer the location from an IP address or an unrelated office address.
4. If no candidate is supported, return `unresolved` with the missing context or source gap. Do not invent an entity or silently select the nearest spelling.

The question must distinguish the *territorial unit or body's identity* from the [service area and physical office address](phase-03-service-channels.md). Even a unique identity match needs separate, reviewed [authority-role evidence](phase-03-authority-roles.md) and applicable service scope before being presented as the competent authority for a procedure. On a saved case, a newly entered name does not replace an existing catalogue ID without explicit user confirmation and a recorded change.

## Current status and acceptance scenarios

The current Milan registry has source IDs, a jurisdiction string and a procedure ID, but no general authority/geography name index or candidate-resolution endpoint. The isolated [candidate matcher](../../backend/app/knowledge/entity_matching.py) implements exact reviewed-name matching, conservative spelling suggestions and ambiguity handling against supplied in-memory records; [synthetic tests](../../backend/tests/test_entity_matching.py) exercise those boundaries. There is still no imported directory, deployed search feature, persisted name review or approval of new aliases. The [Phase 3 search evaluation](phase-03-official-sources-and-catalog.md#28-build-search-over-the-catalogue-and-evidence) will measure recall and ranking when the catalogue exists; task 22.6 will test the broader identifier import and multi-municipality cases.

| Synthetic scenario | Expected result |
| --- | --- |
| The exact current official name and type identify one body. | Return its catalogue ID and the official-name match explanation. |
| A reviewed former name refers to a renamed body. | Return the same stable ID, label the match as a former name and show the current display name. |
| An acronym or English wording identifies more than one body. | Return candidates and ask for the location or entity type that separates them. |
| Two municipalities share a name, or a municipality and province have the same name. | Keep all IDs and types distinct; never resolve by name string alone. |
| A typo or missing accent has one plausible candidate but no confirmed context. | Offer the candidate for confirmation; do not attach it to a case automatically. |
| A query matches an unreviewed alias or no catalogue record. | Keep it unresolved and expose the missing evidence or context. |
| A case already links to a stable ID and the body's display name changes. | Preserve the case link and historical label; show the current name without rerouting the procedure. |
