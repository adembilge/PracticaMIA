# Progress and release status

**Last updated:** 23 November 2026

## Current product surface

The customer root route is the single-chat shell. Legacy customer case, account and synthetic demo pages were removed in merged PR #245. The customer navigation is conversation history only.

The backend is not yet fully migrated: case-named API routes, internal model/service dependencies, feature flags and database tables remain. The cleanup is tracked in [the legacy migration plan](LEGACY_MIGRATION_PLAN.md); no production records or tables have been deleted.

The conversation transport and worker are still restricted to isolated development/Preview infrastructure. Production chat execution is not enabled. No deployment, live Auth0 journey or production acceptance is claimed by the source cleanup.

## Phase 4

- Task 34.6: bilingual authority spelling suggestions remain confirmation-only; exact-name/near-match collisions remain ambiguous. PR #244 merged as `27f853507e9f48caea2ecb506cb42738382793d`.
- Next: Task 35.1 clarification context check.
- Phase 5 remains paused.

## Legacy cleanup milestone

- PR #266 merged: consolidated cleanup execution plan and target model draft.
- M2.4 completed: source-to-target mapping, ownership/cardinality, conversation/task deletion, retention, AAD versioning and runtime uniqueness/receipt constraints are documented in `TASK_CONVERSATION_TARGET_MODEL.md`.
- M2.5 encrypted-payload strategy is documented and now deferred by project-owner decision; no further review work is planned. This does not authorize live key access, schema changes or data migration.

## Legacy cleanup milestone

- PR #267 merged: M2.4 target conversation/task ownership model completed.
- PR #268 merged: M2.5 encrypted-payload migration strategy and consistency baseline completed.
- PR #269 merged the coordinated M3 disposable migration harness.
- Added isolated crypto primitives for key-family preflight, canonical destination AAD v2, authenticated decrypt/validate/re-encrypt/verify, owner/link validation and retention checks.
- Added disposable PostgreSQL staging/ledger tests for atomic writes, retry revalidation, orphan-target rejection and rollback; wired into backend CI.
- Full source-table migration, target Alembic schema and non-disposable execution remain blocked pending engineering/security/operator approval and deployed key-custody evidence. No production or staging data/key access or mutation has occurred.

## Verification boundaries

Backend and frontend CI results apply to their tested revisions and environments. Synthetic fixtures do not establish participant evidence, live legal validation, broad municipal coverage or production readiness. Real personal-document upload remains disabled pending independent privacy and operational reviews.

See [active work](ACTIVE_WORK.md), [acceptance status](ACCEPTANCE_TESTING.md), and [product specification](PRODUCT_SPECIFICATION.md).
