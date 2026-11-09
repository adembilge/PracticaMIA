# Synthetic MVP acceptance suite

This is an **automated end-to-end acceptance rehearsal**, not permission to
handle real municipal documents or a completed production launch.

## What is actually tested

The dedicated GitHub Actions workflow
`.github/workflows/mvp-acceptance.yml` launches:
- An **isolated PostgreSQL 17 + pgvector** service with the repository's
  complete Alembic migrations (no Neon production connection).
- The real FastAPI application with all case, scope, intake, workflow,
  checklist-review and package-PDF endpoints enabled.
- Ephemeral RSA-2048/RS256 signed bearer tokens for two synthetic principals
  (**alice** and **bob**), verified with the application's genuine JWT
  verifier. The JWT signer exists only in the local CI server process.
- The real `SavedCasesView`, `SavedCaseWorkspace`, `CaseIntakePanel`,
  `CaseJourneyPanel`, and `DemoProvider` React components bundled into a
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
| A8 | No uncaught browser runtime errors | Chromium |
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
  health checks. No Vercel operations are authorized.
- Real third-party malware scanning, controller/privacy approvals, backup
  and retention operations, live identity uploads, production OCR or data
  processing agreements.
- Current official municipal website content or legal completeness.
  A synthetic source fixture exercises downstream invalidation, while
  separate repository tests exercise real provenance checks.
- A full conversational LangGraph agent evaluation, human usability study,
  document OCR benchmarks, or administrative submission.

These are separate **release acceptance gates** and must not be silently
treated as passed merely because synthetic E2E is green.

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

The fixture contains only synthetic names, dates and typed fields; no
private personal records or external government submissions are used.
