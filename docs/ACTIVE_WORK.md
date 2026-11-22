# Active work

**Current phase:** Phase 4 — agent and conversation engine  
**Current task:** 35.1 — clarification context check  
**Next task:** reuse already confirmed information and accessible document results before asking a clarification. Do not repeat a question when the required information is already available.

## Current state

- Task 34.6 spelling confirmation and ambiguous authority-name collision protections are merged.
- PR #244 was merged as `27f853507e9f48caea2ecb506cb42738382793d9`.
- This cleanup PR moves the customer entry route to the single-chat shell and removes legacy customer case/demo pages.
- The agent API and worker remain isolated to the reviewed Preview environment. No production enablement is included.
- Phase 5 is paused.

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
