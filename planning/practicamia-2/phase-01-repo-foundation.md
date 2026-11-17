# PracticaMIA 2.0 — Phase 1 · Repository cleanup and rebuild foundation

This phase leaves a clean repository ready for PracticaMIA 2.0 development. Remove the Milan prototype screens, fixed rules, and previous project documentation from the active codebase. Review and retain reusable infrastructure, verifiable official-source records, and safe test documents. Close the phase when the application and an empty database can be set up from a clean checkout.

**Starting inventory.** The earlier repository inventory found 348 files and 41 Markdown documents. The old 94-task plan is linked to `AGENTS.md`, `docs/MASTER_PLAN.md`, `docs/TASKS.yaml`, and CI validation. Refresh the inventory when implementation begins. Cleanup covers the active codebase. Retain the previous Git reference for rollback and decision history.

## 1. Pin the existing release and open the working branch

- **1.1** Record the `main` commit, open pull requests, and the latest successful frontend, backend, and browser tests. Check whether open PRs overlap files scheduled for cleanup.
- **1.2** Record live web and API deployment IDs, linked domains, and the database migration revision. Inventory the names of environment variables. Keep secret values out of the repository and PR.
- **1.3** Mark the baseline commit with a Git tag such as `archive/practicamia-v1`. The previous plan, source records, and working release code must remain reachable from that reference.
- **1.4** Branch from the pinned commit, for example to `rebuild/phase-01-repo-foundation`. Review preview and CI triggers and verify the isolated environment where tests will run.

**Acceptance.** The old code, live deployments, and database revision are independently identified. The cleanup branch has a known starting commit.

See the [Phase 1 baseline record](phase-01-baseline.md) for the pinned references, test results, and deployment evidence.

## 2. Audit files and dependencies

- **2.1** Inventory `frontend/`, `backend/`, `requirements/`, `audit/`, `evals/`, `scripts/`, `docs/`, and `.github/workflows/`. Mark each item Delete, Keep, Move, or Test before deciding.
- **2.2** Map frontend routes, API proxies, authentication, translation keys, and shared components. Identify the components and API endpoints behind each legacy screen.
- **2.3** Map backend endpoints, services, tables, migrations, and tests. Identify Milan-specific rules and reusable security or data-access components.
- **2.4** Check paths consumed by CI, build commands, deployment configuration, and fixtures. Inspect files with no production callers for build or test dependencies.

**Acceptance.** Each file group has known callers, an expected change impact, and a verification step.

See the [dependency audit](phase-01-dependency-audit.md) and [tracked-file inventory](phase-01-file-inventory.tsv) for the cleanup candidates and checks.

## 3. Identify official documents and evidence to retain

| Material | Phase 1 action |
| --- | --- |
| Previous product plan, progress report, or runbook | Remove from the active branch |
| Official form, public guide, or source record | Keep when origin and version are verifiable |
| Review decision or evidence from an official source | Keep with the associated source, version, and scope |
| Synthetic PDF, image, or OCR fixture | Keep when used in a reproducible test |
| User document or output containing personal data | Track in the private-data inventory and keep outside the repo |

- **3.1** Check for source records and document copies in the database or storage as well as in the repository.
- **3.2** Record the authority, official URL, document title, scope, version, retrieval date if known, and review status. Fingerprint any retained file.
- **3.3** Carry forward an old approval only with the procedure and jurisdiction it covered. Make any Milan-specific scope visible on the record.
- **3.4** Keep official records and test fixtures in separate locations. Verify that synthetic OCR text cannot enter the official catalogue.

**Acceptance.** Each retained document or source record has traceable provenance and purpose. These records remain accessible after legacy documentation is removed.

## 4. Remove previous documentation and roadmap automation

- **4.1** Remove previous plans, progress reports, guides, and pilot reports from `docs/`. Apply the inventory decisions to the root `PracticaMIA_Complete_Project_Specification.md` and old frontend and backend documentation.
- **4.2** Handle `docs/TASKS.yaml`, `scripts/validate_roadmap.py`, its tests, and `.github/workflows/roadmap-governance.yml` as one change group. Clean up jobs that call removed scripts.
- **4.3** Check whether branch protection requires the legacy CI check. If so, run and verify the replacement check before updating the required check reference.
- **4.4** Replace the old `AGENTS.md` with a short working guide. Make the new `README.md` cover product purpose, repository layout, and setup. Use one up-to-date primary file for the 100-task roadmap.
- **4.5** Search for `MASTER_PLAN.md`, `TASKS.yaml`, `validate_roadmap`, and references to the old specification. Remove dangling references in CI, imports, scripts, application copy, and Markdown links.

**Acceptance.** The active branch installs, builds, and tests without referring to the old plan. The entry point to the new documentation is clear.

## 5. Remove the Milan prototype from the application

- **5.1** Trace the old Start a case, fictional scenarios, fixed yes/no flow, and preparation PDF from page to component, proxy, backend, and data.
- **5.2** Remove menus, links, redirects, translations, and visual assets used only by the legacy flow. Redirect legacy URLs needed during the transition to the appropriate new entry point.
- **5.3** Isolate the fixed Milan questions, default procedure, scenario-specific checklist, and fictional package generation. Evaluate reusable document functionality under task 6.
- **5.4** Remove tests specific to the legacy journey. Keep account isolation, file security, and source verification tests or move them to independent entry points.
- **5.5** Assess the impact of code removal on existing records. Plan application cleanup and data deletion as separate changes. Review the migration history needed to read old data or roll back independently.

**Acceptance.** Application startup, login, and the main page work without the old Milan scenario, demo state, or PDF generation pipeline.

## 6. Select and independently test reusable infrastructure

- **6.1** Inspect authentication, record ownership, PostgreSQL connectivity, source permissions, and CI setup. Record the schemas and environment variables involved.
- **6.2** Define independence criteria. Assess the cost of decoupling components tied to the old procedure, city, demo flag, or state model.
- **6.3** Add or move a contract test for each retained component. Cover valid, expired, and unauthorized sessions, and use two identities for record-access tests.
- **6.4** Determine the minimum dependency set for migrated components. Remove unused packages, configuration, and helper scripts. Verify updated lockfiles with a clean install.
- **6.5** Inventory upload, OCR, and PDF tooling and assess reuse. Enable user-facing document capabilities in their corresponding later phases.

**Acceptance.** Every migrated component has a new purpose and a passing test. Shared infrastructure runs independently of legacy demo data.

## 7. Create the new repository foundation

- **7.1** Reuse the `frontend/` and `backend/` roots. Build one frontend application shell with a chat entry point. Later phases add sources, documents, and forms within that shell.
- **7.2** Set up the backend entry point, validated configuration, API versioning, error format, and health checks. Define boundaries for the catalogue, cases, documents, and agent tools.
- **7.3** Implement the initial frontend–backend API contract. Test successful and failed health requests.
- **7.4** Make setup and test examples runnable. Use clear locations for source data, fixtures, and migrations. Add directories with their first file.

**Acceptance.** One web application and one backend run. A browser can make a real health request to the backend.

## 8. Make environment and database setup reproducible

- **8.1** Define database, identity provider, and storage targets for local development, CI, preview, and production. Return a clear startup error for missing or invalid critical configuration.
- **8.2** Update `.env.example` files with required keys and safe sample values. Keep real credentials and test account details in environment secrets.
- **8.3** Install the new development schema on an empty database. Record whether to extend the previous migration chain or introduce a separate 2.0 schema, including legacy access and rollback implications.
- **8.4** Separate migration and fixture seeding commands. Test that seeding rejects production targets and creates no duplicate records when rerun.
- **8.5** From a clean checkout, verify dependency installation, configuration, migration, seed data, and first startup using the `README.md`. Repeat to confirm no leftover local setup is required.

**Acceptance.** An empty test environment can be recreated without old Milan cases or production secrets.

## 9. Connect CI to the new foundation

- **9.1** Run dependency installation, type checking, tests, and a production build in frontend CI. Verify the new home page and health connection over HTTP.
- **9.2** Run migrations on empty PostgreSQL, API health checks, and retained session and access tests in backend CI.
- **9.3** Scan for legacy file paths, broken repository links, requests to removed routes, and leaked secrets. Record findings in the PR.
- **9.4** Add small browser checks for the application shell, correct sign-in destination, and the visible state when the backend is unavailable.
- **9.5** Align working jobs with branch checks. Make failures identifiable as build, migration, permission, test, or deployment issues.

**Acceptance.** CI passes from a clean installation and has no dependency on the previous roadmap or demo flow.

## 10. Finish the cleanup PR and close the phase

- **10.1** Record removed components, moved source records, reused infrastructure, and the previous Git reference in the PR.
- **10.2** Review the diff against the baseline. Recheck source records, branch protection, and environment targets.
- **10.3** Link clean checkout, empty-database migration, frontend build, backend tests, browser checks, and preview health results to the PR.
- **10.4** Merge the verified cleanup PR and check `main` results. Pin the repository structure, commands, and baseline commit for Phase 2.

| Closure check | Expected evidence |
| --- | --- |
| Previous documentation and automation removed | No active file, CI job, or reference depends on the old plan |
| Official documents and evidence retained | Records are discoverable by authority, source, version, and scope |
| Legacy Milan flow removed | The new application has no dependency on demo pages, fixed questions, or the previous PDF flow |
| New foundation works | Clean checkout, empty database, running web app, and successful API health check |
| Rollback point available | Previous Git revision, deployment IDs, and schema revision recorded |

**Implementation order.** Start with 1 → 2 → 3. Then remove legacy documentation and the prototype, verify reusable components, and set up the new foundation and CI. Phase 2 starts after clean setup and CI results have been verified on `main`.
