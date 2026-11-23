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
- M2.5 is the next cleanup design item. No schema, data, encryption, deployment or production execution changes are authorized by M2.4.

## Legacy cleanup milestone

- PR #267 merged: M2.4 target conversation/task ownership model completed.
- M2.5 design baseline completed in `ENCRYPTED_PAYLOAD_MIGRATION_STRATEGY.md`: encrypted payload inventory, source AAD, key configuration, write-fence strategy, retention races, idempotent ledger, dry-run gates and recovery boundaries are documented.
- M2.5 engineering/security/operator review and deployed key-custody evidence remain pending. M3 is blocked; no schema, data, key or ciphertext changes were made.

## Verification boundaries

Backend and frontend CI results apply to their tested revisions and environments. Synthetic fixtures do not establish participant evidence, live legal validation, broad municipal coverage or production readiness. Real personal-document upload remains disabled pending independent privacy and operational reviews.

See [active work](ACTIVE_WORK.md), [acceptance status](ACCEPTANCE_TESTING.md), and [product specification](PRODUCT_SPECIFICATION.md).
