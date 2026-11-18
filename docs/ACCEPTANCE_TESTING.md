# Synthetic case acceptance suite

This is an **automated end-to-end acceptance rehearsal**, not permission to
handle real municipal documents or a completed production launch.

## What is actually tested

The dedicated GitHub Actions workflow
`.github/workflows/mvp-acceptance.yml` launches:
- An **isolated PostgreSQL 17 + pgvector** service with the repository's
  complete Alembic migrations (no Neon production connection).
- The real FastAPI application with all case, scope, intake, workflow,
  checklist-review and package-PDF endpoints enabled. The document run also
  mounts the private upload, extraction, review, deletion and expiration routes
  with fresh process-local keys and an isolated fixture scanner.
- Ephemeral RSA-2048/RS256 signed bearer tokens for two synthetic principals
  (**alice** and **bob**), verified with the application's genuine JWT
  verifier. The JWT signer exists only in the local CI server process.
- The real `SavedCasesView`, `SavedCaseWorkspace`, `CaseIntakePanel`,
  `CaseJourneyPanel`, `PrivateDocumentsWorkspace`, and `DemoProvider` React components bundled into a
  localhost-only browser harness using pinned CI-only esbuild/Playwright.
- Headless Chromium controlling the actual case screens, forwarding their
  API calls over HTTP to FastAPI. The only replacements are a minimal
  Next navigation adapter and the Auth0 browser-session proxy, which are
  *not* part of production builds.
- A **clearly marked synthetic, first-route source resolver** for the
  previously signed catalog, with an explicit revocation/reapproval control.
  Separate backend contract tests verify the actual source snapshot approval,
  passage integrity, signature and revocation logic.

## Acceptance scenarios

| ID | Expected behavior | Layer |
|---|---|---|
| A1 | Create case, answer all five product questions, confirm typed intake and see signed actions | Chromium + real FastAPI + PostgreSQL |
| A2 | Acknowledge five read actions, reload and retain progress, download real generated PDF | Chromium + real FastAPI + PostgreSQL |
| A3 | Unauthenticated and different-account access denied, including package export | Chromium + real FastAPI + PostgreSQL |
| A4 | Simulated source revocation blocks PDF and actions; restored evidence invalidates stale marks | Chromium + real FastAPI + PostgreSQL, **synthetic trusted-source fixture** |
| A5 | Edited intake outside the route blocks draft; restored facts need fresh review marks | Chromium + real FastAPI + PostgreSQL |
| A6 | Unsupported or uncertain initial answers cannot export | Chromium + real FastAPI + PostgreSQL |
| A7 | Italian language uses the same verified case state and downloadable draft decisions | Chromium + real FastAPI + PostgreSQL |
| Preparation Preview | Mobile deep link, upload and OCR waiting states, reduced motion, 503 feedback, back navigation, draft retention and load retry | Chromium with stubbed preparation responses |
| Agent reconnect | Discover a paused conversation in a fresh browser context, restore its question, retry a lost reply response, verify account isolation and display the result committed by the background worker | Chromium + signed synthetic JWT + FastAPI + PostgreSQL |
| Agent stop | Refresh the current status after a stale stop request, confirm the next request stops the conversation, and verify the terminal event and active list after reload | Chromium + signed synthetic JWT + FastAPI + PostgreSQL |
| A8 | No uncaught browser runtime errors | Chromium |
| D1 | Explicit acknowledgement required, malformed uploads rejected, scanner outage/checksum/control verdict rejected, browser retry works | Chromium + real ClamAV with a harmless test signature + FastAPI + PostgreSQL |
| D2 | Extract PDF fields, reject stale review, block PDF while a confirmed field conflicts, correct it and reopen the saved review | Chromium + FastAPI + PostgreSQL |
| D3 | OCR of PNG, JPEG and scanned PDF, two supported fields matched on each, real PDF with status-only metadata and ANPR link | Chromium + local Tesseract/PDFium + FastAPI + PostgreSQL |
| D4 | Anonymous and second-account read/write/export denied. Original bytes have no download handler | Chromium + FastAPI + PostgreSQL |
| D5 | Seven-day timestamp, inaccessible expired review, authorized purge and immediate owner deletion | Chromium + FastAPI + PostgreSQL, locally advanced synthetic record only |
| API | Document extraction/correction, conflicts, encrypted review tampering, expiry, citation URL/signature failures | FastAPI TestClient with synthetic fixture/scanner, in the dedicated acceptance job |

The CI job produces `frontend/.acceptance-results/acceptance-report.json`,
an isolated server log and screenshots on browser failures. The GitHub Actions
artifact `synthetic-mvp-acceptance` retains these for 14 days. All scenario
failures cause a **nonzero** exit and a failed required job if branch protection
is configured accordingly. The job must be green before accepting the
synthetic-thesis demonstration.

### Why this is not production acceptance

This suite deliberately does **not** cover:
- A real Auth0 browser login/callback, refresh-token or cross-domain session.
  The harness tests the genuine FastAPI JWT verifier but not the Auth0
  provider and Next.js BFF session wiring.
- Vercel or another live deployment, hostname, production secrets or live
  health checks. Hosted checks use the separate workflows below.
- Real third-party malware scanning, controller/privacy approvals, backup
  and retention operations, live identity uploads, the hosted OCR runtime or data
  processing agreements.
- Current official municipal website content or legal completeness.
  A synthetic source fixture exercises downstream invalidation, while
  separate repository tests exercise real provenance checks.
- A full conversational LangGraph agent evaluation, human usability study,
  document OCR benchmarks, or administrative submission.

These are separate **release acceptance gates** and must not be silently
treated as passed merely because synthetic E2E is green.

## Manual production Auth0 check

**14 November 2026** · [Production web](https://practicamia.vercel.app) · web and API on [`24ee003`](https://github.com/adembilge/PracticaMIA/commit/24ee003050c13eab6b5ca40e14f7f3ff87a93514)

| Assertion | Observed result |
| --- | --- |
| Real browser sessions | Two signed-in accounts had distinct Auth0 subjects. Subjects and credentials are omitted from this record. |
| Owner opens the fictional case | The saved workspace loaded with all five acknowledgements preserved. |
| Owner downloads the preparation draft | The project owner confirmed a successful download. Browser automation timed out waiting for its download event during the repeat attempt. |
| Second account lists saved cases | The owner case was absent. The signed-in list loaded without an error. |
| Second account opens owner case directly | The UI displayed `Case unavailable`. The case API returned `Case not found`. |
| Second account opens the owner's PDF link | The PDF endpoint returned `Preparation package unavailable` as JSON. No PDF was served. |

The manual check covers live Auth0 sign-in, saved-case persistence and read isolation for the selected case and preparation draft. It does not exercise cross-account writes, private document upload or reviewer authorization. The [authenticated Preview runbook](AUTHENTICATED_PREVIEW_E2E_RUNBOOK.md) covers a separate staging workflow.

## Manual staging case and document checks

| Date | Observed result | Coverage |
| --- | --- | --- |
| 14 Nov 2026 | Owner reopened a fictional case with all five acknowledgements, saw the ANPR handoff and confirmed the PDF download. A separate unsupported case blocked export. The second account could not list or open the owner's case, and the owner reported 404 on the second account's scope PATCH and PDF GET. | Saved-case journey and selected ownership checks. See [progress](PROGRESS.md#verified-engineering-evidence) for the tested revisions. |
| 15 Nov 2026 | On [isolated Preview `a493d46`](https://github.com/adembilge/PracticaMIA/commit/a493d46bf768d07d196d29789e99d51b3b181a86), an authenticated user uploaded a fictional PNG. **Extract text** returned 503 and the document stayed `not_processed`. | Synthetic upload passed. The browser showed only the response status. Hosted OCR success, the private-document upload proxy, and the live malware scanner have no pass evidence. |
| 15 Nov 2026 | On [isolated Preview `973cd49`](https://github.com/adembilge/PracticaMIA/commit/973cd4991c5e5e979527f964fbf6108b17fb9343), the owner reopened a fictional case, saved five checklist acknowledgements and verified 5/5 after reload. The PDF section and download action were visible at 390 px. | The PDF action completed without a visible error, but the browser did not confirm a saved file. The two-account Auth0 check was not repeated for this revision. |
| 15 Nov 2026 | On [isolated Preview `90abb8b`](https://github.com/adembilge/PracticaMIA/commit/90abb8bae6a98986b39ca9581276e0570319ff1c), the same stored PNG moved to **Fields to confirm** after **Extract text**. The expected address `Via Esempio Fittizia 10 Milano` appeared twice as a page 1 candidate and persisted on reopening. | One hosted synthetic PNG passed extraction. Duplicate suggestions remain visible. Hosted private vault, scanner, JPEG, and scanned PDF checks remain open. |

The synthetic preparation route has its own extractor and storage. It does not call the private vault scanner. The [private-document release checklist](PRIVATE_DOCUMENT_VAULT_RELEASE.md) covers the scanner and vault acceptance.

On [isolated Preview `1c89f6f`](https://github.com/adembilge/PracticaMIA/commit/1c89f6f7172724d2e75c9cd5e3189a6fc57abea2), the owner uploaded a synthetic JPEG and an image-only PDF. Each returned one page-one address candidate for the expected fictional address. The field and document reviews persisted after reload. The case PDF action remained available and completed without a visible error. The browser did not verify a newly saved file on this repeat. The earlier owner-confirmed PDF download applies to the saved case draft. See the [package documentation](CASE_PREPARATION_EXPORT.md) for the separate private-document review path.

See the [15 November repeat and bilingual evaluation](MILAN_MVP_ACCEPTANCE_2026_11_15.md) for desktop and 390 px PDF observations, the open Auth0 isolation repeat and the live assistant results.

## Run locally

The dedicated CI workflow runs on PRs, pushes to main, or manual dispatch.
For a developer machine with PostgreSQL, Chromium and Python/Node installed,
follow its commands after setting:

- `DATABASE_URL` and `PRACTICAMIA_ACCEPTANCE_DATABASE_URL` to the **same
  disposable local PostgreSQL database named `practicamia_acceptance`**.
- `PRACTICAMIA_E2E_LOCAL_ONLY=1`.
- `PRACTICAMIA_ACCEPTANCE_ORIGIN=http://127.0.0.1:8765`.

Never point these settings at Neon or a shared database. The bridge refuses
non-loopback hosts and any unexpected database name.

Pass `--private-documents` to the localhost acceptance bridge to include D1–D5.
This run additionally needs `clamscan`, `pdftotext`, DejaVu Sans, and Tesseract
with `ita` and `eng` language data. The app performs its actual request and
checksum validation. Only the network transport to the external scanner is
substituted. The local adapter invokes ClamAV using a dedicated harmless test
signature. It does not use an external scanner, a malware sample, or a vendor
signature database. The test-only controls are served solely by the loopback
bridge and only accept generated fixtures and temporary test identities.

The agent scenarios open the temporary React fixture at `/__acceptance/agent`. The bridge seeds private conversations for choice replies, date replies and stop coverage. A background worker polls the database and processes bounded batches using an expiring lease and a deterministic executor. The browser submits a choice, retries after a lost response, and corrects an invalid date after receiving format guidance. Each accepted reply produces a persisted result. Hosted routes, production frontend navigation, hosted scheduling and provider calls remain outside these tests.

The fixture contains only synthetic names, dates and typed fields; no
private personal records or external government submissions are used.
