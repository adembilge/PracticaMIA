# Milan first-route release acceptance

## ANPR evidence checked on 16 November 2026

The [Comune di Milano FAQ](https://servizicrm.comune.milano.it/centro-supporto/KA-00371/) applies to Italian citizens already registered in Italy moving between Milan addresses or from another Italian municipality. The existing signed path also requires a single adult, no household aggregation and a registered private rental.

The already reviewed [public ANPR guide](https://public-anpr.github.io/anpr-docs-cittadino/src/docs/guide/guida_compilazione_cambio_residenza.pdf), p. 12, shows the **Immobile · Titolo 2** section and the labels **Ufficio di**, **In data**, **Al numero**. They correspond to the municipality of the registration office, rental contract date and rental registration number. Use the pinned, active passage ending in `:0015` for this worksheet. The guide is archived and its labels may differ from the signed-in form.

The public guide describes a per-file size limit, while the [older government-hosted guide](https://sc.anpr.interno.it/serviziCittadino/dist/docs/guida_compilazione_cambio_residenza.pdf) describes an aggregate one. Use the current signed-in form for attachment requirements, supported formats and upload limits. The app does not assert a numeric portal limit. An authorized person must still record the observed live labels, attachment prompts and any stated limits from their own ANPR session, without including personal details or submitting a declaration. If the observed form differs, attach a redacted note to the evidence review and update the mapping through the existing review procedure. The code change neither adds nor approves sources or rules.

## Preparation package

From a confirmed saved case, open **PDF summary**. Review the current case facts, signed actions and the rental worksheet. The three worksheet values stay with the user. The download follows the selected interface language, with the exact signed English action text in English or an explicitly identified Italian translation. Portal field labels stay Italian so the user can recognize them. Original documents and private OCR text are excluded.

Check the English desktop and Italian mobile downloads with the existing Chromium acceptance workflow. Confirm the PDF opens, lists the three cited labels and includes the manual official handoff. Exercise revocation and unsupported cases, and verify the second account cannot download the owner's draft.

## Private vault fixture-only Preview

Use the existing protected `preview/auth-review-isolated` web/API pair, its dedicated Auth0 setup and the isolated PostgreSQL database already identified by the preparation database fingerprint. The preview vault runs the same ownership, scan, encryption, OCR, review and retention machinery used by the private-document path. It accepts exactly two configured Auth0 subject digests, and only server-allowlisted synthetic housing fixture bytes. The allowlist and category are checked before the HTTPS scanner is called.

- Backend Preview variables scoped to that branch: `ENABLE_PRIVATE_DOCUMENT_API=1`, `PRIVATE_DOCUMENT_FIXTURE_MODE=1`, `PRIVATE_DOCUMENT_FIXTURE_SUBJECT_HASHES` (two SHA-256 hex digests of the dedicated test account subjects) and `PRIVATE_DOCUMENT_FIXTURE_FILE_HASHES` (comma-separated lowercase SHA-256 digests of three to twelve generated fixture files). Include PDF, PNG, JPEG and image-only PDF plus the scanner control where available.
- Configure a separate `PRIVATE_DOCUMENT_KEY`, `CRON_SECRET` and authenticated `PRIVATE_DOCUMENT_SCAN_URL`, `PRIVATE_DOCUMENT_SCAN_HOST`, and `PRIVATE_DOCUMENT_SCAN_TOKEN`. Use the approved Preview scanner endpoint. Keep credentials private and scoped to the test deployment.
- Web Preview variables scoped to the same branch: `ENABLE_PRIVATE_DOCUMENT_UI=1` and `PRIVATE_DOCUMENT_FIXTURE_MODE=1`. The web proxy accepts only the existing paired Preview API origin for this mode. Both deployment revisions must reflect the reviewed change.

Sign in with the first dedicated account, create and confirm the synthetic case, upload each format, run OCR, correct a deliberately conflicting field, verify the draft becomes downloadable after correction, then verify deletion. With the second dedicated account, confirm the first account's document listing, upload, extraction, review, deletion and PDF routes are unavailable. Use the approved harmless scanner control to verify a rejection. For the purge drill, use an isolated data copy with an expired synthetic row. Record timestamps, observed statuses, build IDs and backup/restore results, with no Auth0 subjects, file bytes, credentials or document IDs in the report.

## Release evidence still required

- Authorized human observation of the signed-in ANPR form.
- Hosted two-account fixture acceptance with the configured HTTPS scanner and the deployed OCR engine.
- Independent review of the controller/privacy notice, legal basis, scanner/processor terms and retention. Exercise key management, backup recovery and retention monitoring before authorizing real uploads.
