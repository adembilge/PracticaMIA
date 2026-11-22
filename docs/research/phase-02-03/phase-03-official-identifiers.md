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

## Isolated import and acceptance scenarios

The directory importer reads the [IPA Enti XLSX resource](https://indicepa.gov.it/ipa-dati/dataset/5baa3eb8-266e-455a-8de8-b1f434c279b2/resource/d09adf99-dc10-4349-8c53-27b1e5aa97b6/download/enti.xlsx) and [Istat municipality workbook](https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.xlsx). IPA Enti is published by AgID under CC BY 4.0. The Istat workbook identifies its reference date in the data worksheet.

| Workbook | Reference date | Acquisition and ingestion (UTC) | Counts | SHA-256 |
| --- | --- | --- | --- | --- |
| AgID IPA Enti | Unknown for these exact bytes | 17 Nov 2026 22:58:46 / 23:02:19 | 23,771 authority identities | `1a70fe4ffee3713002026c6e921dc32bc31b4cd65976f251e96aef00c5d7c360` |
| Istat Elenco dei comuni italiani | 21 Feb 2026 | 17 Nov 2026 22:59:04 / 23:02:21 | 7,894 municipalities, 110 statistical supra-municipal areas, 20 regions | `83842076860450f7e482daecea6b7a769f5f93d0bf5b0d48802b44896d7a26d5` |

Parser version `1` loaded both original XLSX files into a disposable SQLite catalogue. Re-running the same imports returned the original two batch IDs and left the combined count at 31,795 identities. The SQLite integrity and foreign-key checks passed. Sample verification kept IPA `c_f205` (Comune di Milano), Istat municipality `015146`, Istat statistical area `215`, and region `03` as distinct entries. The application stores the statistical area as the `province` entity kind and retains Istat's subtype value. The file's listing of a statistical area carries no procedural authority.

### Reproduce the import

Install the backend development dependencies and run from `backend/`. Supply the original publisher workbooks and their observed acquisition timestamps. The manifest names the expected resource URLs. The operator must establish that the supplied files came from those URLs and retain the originals under the existing source retention process. The database stores hashes and identity fields. Workbook bytes and IPA contact-person fields stay outside the database and repository.

```sh
python -m app.knowledge.directory_import ipa /path/to/enti.xlsx \
  --database /path/to/phase3-review.sqlite3 --acquired-at "$IPA_ACQUIRED_AT"
python -m app.knowledge.directory_import istat /path/to/elenco-comuni.xlsx \
  --database /path/to/phase3-review.sqlite3 --acquired-at "$ISTAT_ACQUIRED_AT"
python -m pytest -q tests/test_directory_import.py tests/test_entity_matching.py tests/test_service_areas.py
```

Use the same database file for later batches so stable internal IDs and previous observations remain available. New files are validated before writes. The import records changed names, possible inactivity, and identity review candidates when codes reappear, geography parents change, or a newly observed name matches a code missing from the new batch. Review candidates are excluded from automatic continuity mapping. A merger or successor needs dated official change evidence and a recorded decision. The isolated importer does not perform that adjudication or write to the hosted catalogue.

| Synthetic scenario | Expected result |
| --- | --- |
| The IPA Enti file supplies a `Codice_IPA` and name. | Store the code as an external ID with batch provenance; do not infer a procedure role. |
| An old integration supplies only the Amministrazioni layout. | Record it as the legacy format and require an explicit mapping to the selected Enti import. |
| Two Istat exports use the same permanent URL but different reference dates or bytes. | Preserve distinct batch records and hashes; never overwrite the older import evidence. |
| A code or name differs across dated territorial reports. | Keep the source dates and flag the mapping for task 22.5 rather than silently reassigning an existing case. |
| A dataset has no stated release date. | Keep that date unknown while retaining acquisition and ingestion timestamps. |
| A file lacks a required identifier column or has conflicting duplicate keys. | Reject the batch before any catalogue write. |
