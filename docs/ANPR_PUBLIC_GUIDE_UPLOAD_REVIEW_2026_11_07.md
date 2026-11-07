# ANPR residence-change public-guide upload: source-specific review record

**Review date:** 2026-11-07. **Decision:** FIELD-LEVEL EVIDENCE RECONCILED; **NOT AN ADMINISTRATIVE SOURCE APPROVAL**.

## Artifact inspected

- User-provided original filename: `guida_compilazione_cambio_residenza.pdf`
- SHA-256 of the *exact uploaded local file*: `7ecc161913692a6d6102931c1b8cba368647a69ce664fd682785cdfd5fbadd81`
- Size: **1,502,022 bytes**; **29 PDF pages**; A4
- PDF metadata: title `Dichiarazione Residenza - Modalità operative per il cittadino`, author `ANPR`, creation/modification date **2025-04-08 13:45:45 UTC**.
- Public documentation page carrying a PDF with the same visible guide:
  https://public-anpr.github.io/anpr-docs-cittadino/src/docs/guide/guida_compilazione_cambio_residenza.pdf
- GitHub organization: https://github.com/public-anpr/anpr-docs-cittadino
- These observations are not a cryptographic verification that this user-uploaded file is byte-for-byte identical to the currently hosted URL. The metadata creation date is not proof of a document's legal validity or currentness.
- **Do not import these bytes using the existing Ministry source ID** `anpr-citizen-residence-guide`, whose registered source URL is `sc.anpr.interno.it`. That would misrepresent provenance and cause source URL/integrity mismatch.

## Exact narrow procedure

Only the first MVP scenario: **one adult Italian citizen already resident in Italy**, moving **alone** to **Comune di Milano**, **not joining an existing anagraphic family**, occupying a home as the holder of a **regularly registered private rental agreement**. This is product scope, not a declaration of the applicant's legal eligibility.

## What the inspected PDF actually says (printed page numbers)

| Source page | Section | Field or instruction | Implementation consequence |
| --- | --- | --- | --- |
| 2 and 5 | General / tipologia | `Nuova residenza` covers a home without other people or with unrelated co-occupants; family aggregation is a different route | Keep five-question scope, not automatic legal approval |
| 7 | 1.1.1 Famiglia | Select moving applicant, relationship to household head, driving-licence yes/no, vehicles yes/no | Keep questions, do not fabricate a family relationship |
| 8 | 1.1.2 Residenza | Required `Provincia`, `Comune`, **single `Indirizzo` field**, `Civico`, `CAP` | **Fix older draft** which incorrectly split street type/name and ALTRO |
| 8 | 1.1.2 Residenza | Optional `Località`, `Frazione`, `Scala`, `Piano`, `Interno`, `Esponente interno` | Add optional worksheet fields; never mark mandatory |
| 12 | 1.1.3 Immobile | Registered rental uses option **2** and `Ufficio di`, `In data`, `Al numero`; text calls the date `data del contratto di locazione` | Rename erroneous `rental_registration_date` to **`rental_contract_date`** |
| 14–15 | **1.1.4 Dati di contatto** | Up to two telephone numbers and a period when resident can be reached for municipal check | Correct section number, add second optional phone; do not assert current mandatory status |
| 15–16 | **1.1.5 Allegati** | Generally optional attachments, `pdf` / `jpg` / `png`, maximum **1 MB per file** **in this edition**; mandatory residence permit **for non-EU citizens**, excluded from first scope | Do not demand Italian tenant upload or enforce this historical limit in app |
| 18–19 | 1.1.6 Riepilogo | Applicant checks and sends on official ANPR; subsequent review by municipality | PracticaMIA never submits or claims municipality acceptance |
| 26–28 | 1.3 Le tue richieste | Distinguishes draft, submitted, awaiting co-validation and further municipal status checks | Do not label a local preparation worksheet as submitted |

This PDF's section order **differs** from indexed text of the Ministry-hosted document:
- Uploaded public-guide edition: **1.1.4 Dati di contatto**, **1.1.5 Allegati**.
- Older indexed Ministry-hosted variant reported: **1.1.4 Allegati**, **1.1.5 Dati aggiuntivi**.
- The Ministry-hosted URL was not retrieved as original bytes in this work session; do not claim that the two editions are interchangeable or impose the alternate limit.

## Independent municipal corroboration

- Comune di Milano official service: https://www.comune.milano.it/servizi/anagrafe/cambio-di-residenza (SPID/CIE, within 20 days, municipal verification and separate TARI).
- Comune di Milano FAQ: https://servizicrm.comune.milano.it/centro-supporto/KA-00371/ (one adult Italian already in Italy, 20-day ANPR notice, separate TARI). The Preview knowledge registry already contains hash-reviewed passages for this FAQ.
- No automatic inference from the **foreign-national renter attachment** FAQ `KA-00329` to this Italian citizen route.

## What has been done in code

- `requirements/milan-residence-change/individual_registered_rental_anpr_field_review_v1.json` is now v3 with uploaded-copy metadata, exact guide-section labels, corrected date/address fields, and separate official-source approval status.
- `backend/app/preparation/anpr_draft.py` exposes the inspected hash and optional fields in the existing synthetic worksheet.
- Regression tests check the edition fingerprint, no mandatory Italian-tenant upload assertion, correct section numbers and user-only ANPR handoff.

## What approval still means

**The uploaded file has not been stored as a source snapshot version in the isolated Neon source registry,** and the source's publisher identity and **current 2026 ANPR live-portal correspondence are not yet independently attested.** The existing registered Ministry PDF candidate has *zero* source versions. Registration, source import, authenticated API approval, and final human-signed rules catalog are separate steps.

Use a source candidate with the **real provenance URL** if the public documentation PDF is chosen for controlled staging evidence. Do not bypass `validate_candidate`, change the approved institutional attribution, or associate this upload with a Ministry-hosted canonical URL. The goal is an accurate MVP, not a green status obtained by inventing evidence.

**No source review audit event, reviewer signature, real-data handling, or government submission has been performed here.**
