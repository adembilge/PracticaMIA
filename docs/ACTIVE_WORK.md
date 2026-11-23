# Active work

**Current phase:** M3 — conversation/task data migration  
**Current task:** M3 disposable implementation and synthetic validation complete; live migration deferred and unauthorized  
**Next task:** No further M3 work is authorized while M2.5 remains deferred; do not begin M4 destructive cleanup or Phase 5.

## Current state

- Task 34.6 spelling confirmation and ambiguous authority-name collision protections are merged.
- PR #244 was merged as `27f853507e9f48caea2ecb506cb42738382793d9`.
- PR #245 is merged: the customer entry route is the single-chat shell; legacy customer case, account and demo pages are removed.
- Full backend migration is not complete. Case-named API routers, internal models, feature flags and database tables remain. See [legacy migration plan](LEGACY_MIGRATION_PLAN.md).
- The agent API and worker remain isolated to the reviewed Preview environment. No production enablement is included.
- Phase 5 is paused.

## Current cleanup priority

M2.5 is deferred by project-owner decision. PR #269 delivered the disposable M3 harness and PR #271 merged synthetic round-trip coverage for all nine encrypted payload families. The safe, disposable M3 implementation is complete. Live source-to-target migration, target application schema and cutover remain unexecuted and unauthorized; no production or staging data or keys were accessed. Do not drop or rewrite stored records. Phase 5 remains paused.

## Cleanup milestone status

- M2.4 target conversation/task ownership model: complete; see `TASK_CONVERSATION_TARGET_MODEL.md`.
- M2.5 encrypted-payload strategy: design baseline retained; work deferred by project owner.
- M3 disposable harness: complete and merged in PR #269; see `M3_MIGRATION_IMPLEMENTATION.md`.
- M3 disposable implementation and synthetic payload-family validation: complete (PRs #269 and #271). Live migration and cutover: deferred because M2.5 was deferred; not authorized or executed.
- M4 runtime removal remains blocked on successful M3 migration and recovery approval.

## Phase 4 priorities

1. Improve clarification context reuse without treating inferred or unconfirmed values as facts.
2. Increase bilingual synthetic scenario coverage while preserving abstention and authorization gates.
3. Keep authority identity suggestions in `needs_confirmation`; do not auto-select a near match.
4. Keep ambiguous procedures, authorities and assistance channels unresolved.
5. Record the exact test evidence and known limitations for each increment.

## Evaluation boundaries

Synthetic scores measure only the named fixtures and journey. They are not participant evidence, live source review, legal validation or production readiness. Do not claim 100% overall success from a scoped suite.

## Deployment and quota policy

Avoid unnecessary Vercel deployments. Prefer one consolidated PR per bounded cleanup or task increment. Do not change Vercel project settings, quotas, billing, permissions or production aliases. GitHub pushes may still trigger the repository's configured Vercel integration.

## Data preservation

Source-code cleanup does not authorize deleting production records, dropping legacy database tables or rewriting owner bindings. Internal task storage can be redesigned only through a separately reviewed migration with verified ownership, recovery and retention behavior.
