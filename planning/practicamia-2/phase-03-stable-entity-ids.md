# Phase 3.8 — Stable catalogue identities and names

[PracticaMIA 2.0 task 22.2](phase-03-official-sources-and-catalog.md#22-import-italian-authority-and-geography-identifiers) keeps external directory codes, internal catalogue identities and names independent. The [IPA and Istat batch contract](phase-03-official-identifiers.md) supplies provenance for codes and names; an imported row does not by itself establish a body's procedural role or a service jurisdiction.

## Identity contract

| Field | Meaning |
| --- | --- |
| `catalogue_id` | An opaque, stable internal ID for one authority or territorial unit. Case, procedure and evidence relationships use this ID; never derive it from a display name or replace it during a rename. Keep authority and geography ID spaces distinct. |
| `external_id` | A code in a named source system, such as IPA `Codice_IPA` or an Istat statistical-unit code, linked to the exact import batch and its reference date. Keep the original string and its namespace. An external code may change without changing the internal ID. |
| `display_name` | The currently selected human-readable name, with language and source. Name changes create name history; they do not rewrite the entity ID or historical case record. |
| `name_history` | Earlier official names and their evidenced dates or dataset releases. Preserve an unresolved start/end date as unknown. An alias or spelling variant is separately labelled and cannot silently become an official former name. |

Resolve an imported row to an existing catalogue ID only when the entity match is supported by its official identifier and dated change evidence. A matching name alone is insufficient: two municipalities or a municipality and a province may share a name. If an external code is reused, retired, recoded or ambiguously mapped, hold the proposed link for review. Never reassign an existing ID to a different body or territorial unit. Task 22.5 will define the import diff and approved merge/inactivation operations; this contract fixes the identities those operations must preserve.

Saved cases and procedure assignments refer to the internal ID. A historical case can retain the label shown at the time for audit, while a current view resolves the present display name from that same ID and makes a rename visible. If an entity was dissolved or merged, keep the old case reference and record an explicit successor relationship only after the official change is reviewed; do not silently redirect the case to a new competent authority. A new procedural role still requires the [authority-role evidence](phase-03-authority-roles.md) for that procedure and scope.

## Current status and acceptance scenarios

The existing Milan knowledge registry stores `KnowledgeSource.id`, a jurisdiction string and a procedure ID, but no general authority or geography entity table, external-ID mapping or name history. This design does not migrate saved cases or alter those strings. No IPA or Istat file has been imported.

| Synthetic scenario | Expected result |
| --- | --- |
| An authority changes its official display name while retaining a verified IPA identity. | Keep its catalogue ID and case links; add the new name with batch provenance. |
| A territorial unit receives a different Istat code in a later dated report. | Keep the internal ID only after the continuity mapping is reviewed; retain both dated external-code records. |
| Two units share a display name. | Return distinct catalogue IDs and require a distinguishing location or type. |
| A name matches a municipality and a province. | Keep their entity types and IDs separate. |
| A legacy case refers to an entity by an old name. | Preserve the original reference and label; do not change the underlying entity by string matching. |
| A merger or inactive record has no reviewed successor mapping. | Keep historical links and leave current routing unresolved. |
