# PracticaMIA rules activation — authorized reviewer handoff

**Recorded research: 7 November 2026. Status: NOT ACTIVATED.**

## Decision and boundary

The owner has authorized technical work toward activation. A message approving
"everything" is not an authenticated source-review API call, source-version
attestation or cryptographic signature, and cannot establish source completeness.
Do not enter a fake Auth0 subject, reviewer audit event, signature or municipal
publication date. This is an internal product approval process; no Comune di
Milano permission or governmental accreditation is implied.

## Concrete official sources and the unresolved ANPR guide version

1. Comune di Milano, [Italian change of residence FAQ](https://servizicrm.comune.milano.it/centro-supporto/KA-00371/),
   last updated 23 July 2026: communicate to Anagrafe within 20 days via
   ANPR; household aggregation consent is a **different case**; TARI
   declaration is separate. Exact vetted excerpt IDs already available in the
   isolated Preview include `e139e910-3a89-4994-b450-b5107d8db7dd:0000`,
   `:0003` and `:0005`.
2. Comune di Milano, [service page](https://www.comune.milano.it/servizi/anagrafe/cambio-di-residenza):
   the route serves moves within Italy and Milan, points to ANPR, requires
   SPID/CIE to enter, and describes municipal verification. This page has
   **no approved original source version for the product yet**.
3. Ministry-hosted [ANPR citizen PDF guide](https://sc.anpr.interno.it/serviziCittadino/dist/docs/guida_compilazione_cambio_residenza.pdf):
   an original PDF version and independent review are still missing.
4. [Public ANPR documentation PDF](https://public-anpr.github.io/anpr-docs-cittadino/src/docs/guide/guida_compilazione_cambio_residenza.pdf):
   publicly readable alternative document, not an interchangeable currently
   approved source. The visible text identifies "Dati di contatto" at
   section 1.1.4 and "Allegati" at section 1.1.5, differing from the
   existing draft mapping. This document states 1 MB **per attached file**
   whereas the indexed Ministry PDF excerpt states 1 MB **in total**.
   Neither limit must be enforced as current until the authoritatively
   applicable source version is independently confirmed.

The source registry now has an **explicit allowlisted** Ministry-domain PDF
candidate `anpr-citizen-residence-guide`. Its inclusion creates no approved
version, no legal checklist and no government submission permission.
The imported PDF reader now accepts original PDFs of up to 40 pages with the
existing 4 MiB file, 250,000-character and passage-count bounds.

## Exact steps to clear the technical gate

### A. Authorized reviewer: acquire and approve each exact source version

- From a permitted browser, download the original complete Ministry-hosted
  ANPR PDF **without editing, screenshots, OCR reprinting or recompression**.
  Check canonical government host, updated/publication information, current
  applicability, the registered-tenant title-2 fields and upload conditions.
- On your **own** machine, from `backend/`, do a dry run:
  `python -m app.knowledge.ingest_source --source-id anpr-citizen-residence-guide --file /path/to/original.pdf`.
  If current PDF exceeds the bounded extractor's limits, resolve by reviewing
  the product importer; do **not** truncate, edit or substitute another PDF.
- Explicitly connect only isolated Neon staging branch
  `preview-preparation-mvp-20261107`, verify its identifier in the Neon
  console, set `PRACTICAMIA_KNOWLEDGE_TARGET=staging`, and run the same
  command with `--apply`. The importer itself also requires a matching
  source row; register the newly curated candidate with the repository's
  normal `register_candidates` setup workflow before ingestion.
- Repeat original-source capture for the Milan service page if applicable.
  Neither web search excerpts nor a retyped source is the original capture.
- Log in via the authorized **Auth0** reviewer identity on the **isolated**
  Preview at `/knowledge/review` and approve the exact pending source
  version hashes only after inspecting the original PDF's text and layout.
  PDF sources require the restricted **individual** review endpoint:
  `GET /api/v1/knowledge/review/versions/{version_id}` then
  `POST /api/v1/knowledge/review/versions/{version_id}/approve`,
  with exact `expected_sha256` and a substantive `review_note`.
  A JWT issued for a subject in `KNOWLEDGE_REVIEWER_SUBJECTS` is required.
  Browser batch approval is only for certain HTML captured articles, not PDFs.

### B. Finalize only the agreed individual registered-rental scenario

- Compare `requirements/milan-residence-change/italian_individual_registered_rental_candidate_v2.json`
  against the approved original passages.
- Confirm all operative fields, conditionally necessary original documents,
  exceptions, and the *user-only* official ANPR handoff.
- Assemble the **final** `backend/app/rules/catalog.json` using only the exact
  engine keys: `version`, `status`, `jurisdiction`, `procedure_id`,
  `approved_by`, `approved_at`, `complete_scenario_coverage`, `rules`.
  Do not copy `proposal_only`, `scope_note` or `review_blockers`
  into the final signed catalog; they are draft-only. Remove or revise any
  incorrect condition or administrative claim, and cite precise approved IDs.
- After the authorized reviewer verifies completeness, use
  `status: "active"`, `complete_scenario_coverage: true`, their actual
  reviewer identity and timestamp. The software **must not** infer approval
  from the current conversation or fill the reviewer fields automatically.

### C. Sign final catalog offline; never put the private key in ChatGPT

The signing helper is now available at `backend/app/rules/offline_sign.py`.
On the reviewer's trusted machine, generate or use a separate private key:

```sh
openssl genpkey -algorithm ED25519 -out reviewer_ed25519.pem
chmod 600 reviewer_ed25519.pem
cd backend
python -m app.rules.offline_sign \
  --catalog app/rules/catalog.json \
  --private-key /private/path/reviewer_ed25519.pem \
  --output /private/path/signed_catalog.json \
  --public-key-output /private/path/reviewer_public_key.b64
```

The helper only accepts a structurally complete, explicitly active catalog,
rejects incomplete or draft metadata, signs the same canonical JSON verified
by the backend, and verifies the result before writing output. It does
**not** check the actual live knowledge DB, verify municipal law, record
Auth0 source reviews, manage keys or deploy the application. Keep the
private key strictly offline and outside all chat, repository, CI and Vercel
settings.

Commit the **reviewed signed catalog** as
`backend/app/rules/catalog.json` through a reviewed PR. Set the base64
**public** key only in the matching isolated backend Preview environment as
`PREPARATION_RULE_REVIEW_PUBLIC_KEY`.

### D. Accept only actual observed activation

- CI: validate signature mutation, wrong route, unknown fields, missing
  citations and revocation; no test fixture may activate the deployed catalog.
- Vercel: deploy the reviewed commit to both matching isolated Preview
  projects only once the Hobby deployment quota permits. Production is not
  a permitted deployment target for this milestone.
- Live: use two synthetic Auth0 users. Confirm only the correct five-part
  narrow scope yields a requirements decision of `supported`, and every
  missing or revoked cited source blocks the checklist and handoff.
- The government service is only ever **opened by the applicant**;
  PracticaMIA does not submit a declaration or claim acceptance.
- Privacy, real-document screening, document retention and a real-user
  production release remain **separate gates**.

## Status as of this repository change

**Complete:** source research, candidate narrow route, source registry entry,
bounded PDF importer support, documented guide conflicts, offline signature
helper and synthetic regression tests.

**Not complete:** original PDF acquisition, currentness reconciliation,
authenticated reviewer approvals for required source versions, final signed
catalog, matching READY frontend deployment and authenticated live E2E. None
has been silently marked done on behalf of the project owner.
