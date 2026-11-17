# Phase 3.7 — Official authority and geography identifiers

[PracticaMIA 2.0 task 22.1](phase-03-official-sources-and-catalog.md#22-import-italian-authority-and-geography-identifiers) uses official directories to identify public bodies and territorial units. Directory identity is separate from the [role a body plays](phase-03-authority-roles.md) in a procedure and from the jurisdiction supported by a service passage.

## Source selection

| Entity | Official starting point | Use and limit |
| --- | --- | --- |
| Public body | [AgID IPA · Enti](https://indicepa.gov.it/ipa-dati/dataset/enti) | Use its `Codice_IPA` as the external authority identifier. The IPA page identifies this as the current richer dataset; [Amministrazioni](https://indicepa.gov.it/ipa-dati/dataset/amministrazioni) retains the pre-April 2021 file structure for compatibility. Presence in IPA does not prove responsibility for a particular procedure. |
| Municipality, province/metropolitan city, region | [Istat · Codici delle unità amministrative](https://www.istat.it/classificazione/codici-dei-comuni-delle-province-e-delle-regioni/) and its [SITUAS portal](https://situas.istat.it/web/) | Use a dated statistical-unit report and its published codes. Istat directs current and date-specific territorial reports to SITUAS; a municipality name or code must be interpreted against the report's reference date. |

The Istat page also offers a permanent URL for an updated municipality workbook. A permanent download URL is **not** a permanent release identifier: record the workbook's actual reference date and digest each time. For the initial design, do not import a legacy IPA layout merely because an old integration already reads it. If a required SITUAS export cannot be obtained and verified, leave that geographic batch pending rather than substituting an undocumented copy.

## Import record

For each IPA or Istat batch, retain the publisher, dataset name, landing-page URL, exact resource/export URL, file format, publisher-stated release or reference date when available, UTC acquisition and ingestion timestamps, original-file SHA-256, and the parser/schema version. Keep the raw external identifier and name alongside the internal catalogue ID. Record an unknown release date as unknown; never use ingestion time as a substitute. Preserve the original file outside the public case corpus under the project's source retention controls so a later import can be reproduced.

Validate the file type, required columns, identifier syntax and duplicate keys before applying a batch. Import into an isolated database first and compare row counts and selected identifiers with the source report. A re-run of the same file and parser version must not create duplicate catalogue entities. Changes to codes, names or unit boundaries require an explicit old-to-new mapping review in later task 22.5; 22.1 only establishes source selection and batch provenance. Do not assign a procedural role, service channel or approved administrative rule from an identifier row alone.

## Current status and acceptance scenarios

The repository has a Milan-scoped official-source registry, but no general IPA/ISTAT authority or geography import. No official dataset file was downloaded, parsed, approved or loaded as part of this design. The publisher pages were inspected on 17 November 2026; the version and row counts of a future export must be recorded from the file actually acquired.

| Synthetic scenario | Expected result |
| --- | --- |
| The IPA Enti file supplies a `Codice_IPA` and name. | Store the code as an external ID with batch provenance; do not infer a procedure role. |
| An old integration supplies only the Amministrazioni layout. | Record it as the legacy format and require an explicit mapping to the selected Enti import. |
| Two Istat exports use the same permanent URL but different reference dates or bytes. | Preserve distinct batch records and hashes; never overwrite the older import evidence. |
| A code or name differs across dated territorial reports. | Keep the source dates and flag the mapping for task 22.5 rather than silently reassigning an existing case. |
| A dataset has no stated release date. | Keep that date unknown while retaining acquisition and ingestion timestamps. |
| A file lacks a required identifier column or has conflicting duplicate keys. | Reject the batch before any catalogue write. |
