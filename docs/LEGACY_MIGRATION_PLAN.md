# Legacy case-to-conversation/task migration

**Status:** In progress — inventory and sequencing established 23 November 2026.  
**Product boundary:** one customer-facing conversation at `/`.  
**Data boundary:** preserve existing owner data; no production table or record deletion is authorized by this plan.

## Why this migration exists

PR #245 removed the legacy customer case, account and demo pages. That change did not remove the historical backend case domain. The remaining code is not all dead code: parts of it currently store user-confirmed intake, private-document metadata, checklist review state, workflow drafts, agent proposals and owner-scoped task context.

The goal is to remove the old case-management architecture—not merely hide it—while preserving the useful capabilities as private conversation/task state.

## Confirmed remaining dependencies

### HTTP/API layer

- FastAPI task CRUD router: `backend/app/cases/router.py`, mounted only at `/api/v1/conversations/tasks`. The legacy `/api/v1/cases` CRUD alias has been removed; create/list/read/scope/archive/delete callers and tests use the canonical path.
- Intake API: `backend/app/cases/intake_router.py`, mounted only at `/api/v1/conversations/tasks/{id}/intake`. The legacy `/api/v1/cases/{id}/intake` alias has been removed; the frontend adapter already uses the canonical route.
- Checklist, workflow and package endpoints: `checklist_router.py`, `workflow_router.py`, `package_router.py`.
- Private-document and preparation endpoints still carry case identifiers and case-oriented paths.
- Agent reconnect transport still contains case-linked request/response models and internal thread-to-case link persistence. The former thread task-picker endpoint has been removed; no customer-facing picker is permitted.

### Domain and persistence layer

- `CaseRecord` and `CaseIntake` are still the source of internal task scope and confirmed categorical facts.
- Private-document, preparation, checklist-progress and proposal records reference case IDs.
- `AgentThreadCase` and case-linked agent operations preserve historical links.
- Alembic history contains case-named tables, constraints and foreign keys. Existing records may include encrypted content and audit-relevant state.

### Configuration and documentation

- `ENABLE_DEMO_CASE_API` and `enable_demo_case_api` are still used as backend feature gates and prerequisites for knowledge, preparation and agent features.
- Several runbooks and older research documents retain case-oriented API names. Historical research may remain as provenance, but active product and operational documentation must describe the current chat/task contract.

## Migration sequence

### M0 — Inventory and truthful product documentation

- Record the real remaining backend/API/storage dependencies.
- Correct stale statements that imply the entire backend is already case-free.
- Fix obsolete customer navigation links and dead documentation references.
- Keep Phase 5 paused.

### M1 — Canonical conversation/task API

- Define typed task resource contracts under conversation/task routes.
- Move intake, checklist, workflow and preparation operations behind those routes. Intake is complete: the frontend and backend use only the canonical task route, and the old intake alias is removed.
- Update the frontend BFF to call only the canonical routes.
- Add owner-isolation, CSRF/origin, validation, idempotency and old-route-negative tests.
- Case CRUD alias removal is complete: the canonical task router is the only CRUD mount, and authenticated requests to the old `/api/v1/cases` paths return 404. Other domain-specific compatibility mounts remain separately tracked.
- Do not change storage table names in this step.

### M2 — Internal domain rename

- Removed the unused `/threads/{thread_id}/tasks` listing and its undocumented `/cases` alias; deleted the list-only projection. Internal owner-scoped case binding and resume logic remain because agent execution and approval records still depend on them.
- Replace customer-domain terminology in runtime code with private task/workflow terminology.
- Separate task scope and confirmed user facts from document preparation and agent execution.
- Remove case-selection and thread-to-case linking behavior where the single-chat contract no longer needs it.
- Keep evidence, proposal, approval and owner authorization invariants intact.
- Retain compatibility adapters only where a verified migration still requires them; do not expose them publicly.

### M3 — Data migration

- Design Alembic migrations for task tables and all dependent foreign keys.
- Preserve primary identifiers, owner subjects, timestamps, encrypted payloads, event sequences, checkpoint revisions, retention deadlines and audit history.
- Provide row-count, referential-integrity, owner-isolation and decryptability checks before and after migration.
- Test upgrade and rollback on disposable PostgreSQL snapshots.
- Never drop old tables until the new schema is verified and a recovery window is approved.

### M4 — Removal and final audit

- Remove obsolete case modules, compatibility flags, dead tests and old operational docs.
- Search the full repository for case/demo routes, names, imports, environment variables, migration references and customer copy.
- Distinguish historical research/provenance records from active runtime dependencies.
- Run backend, frontend, browser, PostgreSQL migration, owner-isolation and negative-route suites.
- Report any intentionally retained historical migration or research artifacts explicitly.

## Non-negotiable safeguards

1. No production database mutation or table deletion as part of code-only cleanup.
2. No owner reassignment, cross-owner lookup or loss of encrypted history.
3. No bypass of source approval, user confirmation, human review or production execution gates.
4. No automatic government submission or claim that a draft is officially filed.
5. No Vercel settings, quota, billing or production alias changes.
6. No Phase 5 work until the user explicitly resumes it.

## Completion criteria

The migration is complete only when:

- The public API has no legacy case-management routes or aliases.
- Frontend code calls only conversation/task endpoints.
- Runtime backend code no longer depends on the old case domain or demo feature flag.
- The new task schema contains all required records and passes integrity, owner-isolation, encryption and recovery checks.
- Old tables are removed only after verified migration and an approved recovery process.
- Active docs and tests describe the single-chat product; historical research is clearly marked as historical.
- Repository-wide scans show no active legacy UI/API/runtime references. Historical Alembic migration names and audit evidence may remain where required for reproducibility.
