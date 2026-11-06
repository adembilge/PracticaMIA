# PracticaMIA — verified progress and blockers

**Snapshot:** 6 November 2026 (Europe/Rome)  
**Baseline:** main at `e9404767c7917756dcc7dc19d3b535054823aebe` (independent audit PR #31).

## Evidence already available

| Source | Observed fact | Limit |
| --- | --- | --- |
| [Independent audit PR #31](https://github.com/adembilge/PracticaMIA/pull/31) | Merged; final CI had 225 automated tests passing | Not proof of the complete product |
| [Audit report](audits/INDEPENDENT_SYSTEM_AUDIT_2026_11_06.md) | 10/10 anonymous live HTTP checks, 13 staging source snapshots with verified body and metadata hashes | No authenticated two-account E2E or approved guidance |
| Neon production | Alembic at `20261104_0002` | Behind knowledge schema |
| Neon staging branch | Alembic at `20261106_0010` | Data staging does not establish source approval |
| [Draft PR #32](https://github.com/adembilge/PracticaMIA/pull/32) | Two-account Auth0 browser harness and safeguards; offline/frontend/backend PR CI passed | Live run NOT EXECUTED because isolated preview identity is unconfigured |
| This governance branch | Adds AGENTS instructions and machine-readable source-derived task tracker | Historic task-status evidence not yet reconciled |

## Unresolved delivery blockers

- **P0 — Official administrative evidence:** captured municipal sources remain pending human review; no proven approved source corpus or real embeddings for user-facing guidance. Historical PDF requires independent currency review.
- **P0 — Full MVP:** audited code does not yet provide a verified deterministic rules engine, complete private upload/OCR/field confirmation, full LangGraph case workflow or reviewed application package.
- **P1 — Real preview E2E:** separate Preview Auth0 credentials, paired Preview frontend/backend, reviewer allowlist and two synthetic accounts must be configured without production credential reuse. Follow the [draft PR #32 runbook](https://github.com/adembilge/PracticaMIA/blob/test/isolated-authenticated-preview-e2e/docs/AUTHENTICATED_PREVIEW_E2E_RUNBOOK.md).
- **P1 — Deployment drift:** live frontend/backend revisions and production schema have not been aligned with the audited head. No production migration is authorized.
- **P1 — Task evidence:** historical PRs, source changes, executed tests and explicit human approvals have not been mapped individually to 94 master-plan task acceptance criteria.
- **P2 — Operational release:** backup/restore, sustained load, real mobile accessibility, privacy/retention review and beta validation are not completed.

## Next action: evidence reconciliation

1. Validate the tracker in CI and review this governance PR.
2. Reconcile the 94 parent tasks against actual source code, merged PRs, CI, staging checks, and human approval records. Mark incomplete, partial, blocked and verified-complete separately. Never fabricate sign-off.
3. Clear global task execution blockade only after that evidence review. Then choose the earliest eligible task under the specification's dependency and approval rules.
4. Independently complete the isolated two-account Auth0 Preview setup and run PR #32's opt-in browser workflow. A blocked run is not a pass.

## Future progress entry template

Date; task IDs; base SHA; branch/PR; changed files; tests actually executed and results; production/staging/CI distinctions; human approval evidence; unresolved risks; next eligible action.
