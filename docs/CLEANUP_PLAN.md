# Cleanup and legacy migration plan

**Status:** Active — M2.5 deferred by project owner; M3 disposable harness and synthetic payload coverage implemented; live migration not authorized, 23 November 2026  
**Current phase:** Phase 4; Phase 5 remains paused  
**Primary reference:** [Legacy case-to-conversation/task migration](LEGACY_MIGRATION_PLAN.md)  
**Product contract:** one customer-facing conversation at `/`; internal task/workflow persistence is not a customer-facing task feature.

## 1. Purpose

This document is the execution checklist for removing the remaining legacy case architecture without losing the useful workflow capabilities currently stored behind it. It consolidates completed work, remaining tasks, dependencies, verification gates and explicit non-goals.

This is a code and data-architecture migration plan. It does not authorize production data mutation, table deletion, ownership reassignment, deployment changes or broader product scope.

## 2. Current baseline

- PRs #246–#271 are merged; PR #265 contains the latest runtime change, PR #266 consolidated the cleanup plan, PR #267 completed M2.4, PR #268 documented the M2.5 encrypted-payload strategy, PR #269 implemented the disposable M3 migration harness and PR #271 completed synthetic coverage for all nine encrypted payload families.
- Public legacy case API aliases and customer-facing case/task/demo navigation have been removed in earlier increments.
- Canonical task operations are routed under `/api/v1/conversations/tasks`.
- `ENABLE_TASK_API` is the only supported task-route activation flag and remains disabled by default.
- Case-named internal models, tables, foreign keys and encrypted payload dependencies remain.
- Ownership/cardinality/cascade invariants are covered by tests; archived-task write and worker race boundaries are covered by PR #265.
- No production table or record has been deleted as part of this cleanup.
- Agent execution remains restricted to the reviewed Preview environment; production execution is not enabled.
- Vercel quota/settings and release configuration are outside this plan.

## 3. Completed work

| Work item | Result |
|---|---|
| M0 — dependency inventory and truthful migration plan | Completed; see `LEGACY_MIGRATION_PLAN.md` |
| M1 — canonical conversation/task API surface | Completed; legacy case API aliases removed |
| M2.1 — cardinality and cascade invariants | Completed; PR #264 |
| M2.2 — ownership consistency audit | Completed; no runtime defect found; mismatches must be quarantined, not reassigned |
| M2.3 — archived-task access and write boundaries | Completed; PR #265 merged |
| M2.4 — target conversation/task ownership model | Completed; target contract and compatibility decisions recorded in `TASK_CONVERSATION_TARGET_MODEL.md` |
| Case/demo customer surface cleanup | Completed in earlier merged PRs |
| Legacy demo API setting removal | Completed in PR #257 |

Completed does not mean the underlying case-named database domain has been migrated.

## 4. Remaining work

### M2.4 — Define the target conversation/task ownership model

**Status:** Complete — target model and compatibility decisions recorded in [target data model](TASK_CONVERSATION_TARGET_MODEL.md). No schema or runtime change was made.

Deliverables:
1. Define target entities and responsibilities for conversation, task scope, confirmed intake facts, documents, preparation/review state, agent runs, events, checkpoints and approval/idempotency receipts.
2. Specify cardinality and lifecycle semantics for every relationship, including multiple conversations per task, multiple tasks per conversation if still required, and runs with no task link.
3. Define ownership derivation and enforcement for every target record. Preserve inaccessible ownerless legacy rows as unassigned; never infer or auto-assign an owner.
4. Specify archive, restore, explicit deletion, retention and cascade behavior for each entity.
5. Map every current source table/column to a target entity or an explicitly retained historical record.
6. Record compatibility decisions and explicit constraints that must be revalidated before schema changes.

Acceptance:
- Every current FK edge and runtime read/write dependency has a target mapping.
- Owner isolation, nullable task links, run history, approval receipts and resume semantics are explicit.
- No schema or runtime behavior changes are included in this design task.

### M2.5 — Specify encrypted-payload migration and consistency strategy

**Status:** Deferred by project owner; no further M2.5 review work planned. The design baseline is retained. This deferral does not authorize key access, schema changes, data mutation, re-encryption or deployment changes.

Deliverables:
- Inventory source key configuration and AAD dimensions for each encrypted record class; obtain actual deployed key versions/custody evidence from the authorized operator.
- Define authenticated decrypt → validate → re-encrypt → destination decrypt verification for the destination identity/AAD.
- Use a bounded write fence and staged idempotent ledger; do not dual-write without a separately proven replay/conflict protocol.
- Define idempotency, conflict handling, retry, quarantine and no-plaintext logging behavior.
- Define dry-run evidence, retention race handling, pre-cutover rollback and post-cutover recovery boundary.

Acceptance:
- Every encrypted payload class has a verified migration procedure and failure mode.
- Key unavailability or authentication failure stops migration safely.
- No plaintext payloads are written to logs or audit output.

### M3 — Build and validate the reversible data migration

**Status:** Safe disposable M3 implementation complete (PRs #269 and #271): cryptographic primitives, PostgreSQL staging/ledger harness, and synthetic round-trip tests for all nine encrypted payload families. Live source-to-target migration, Alembic target schema and non-disposable execution are deferred and unauthorized because M2.5 was deferred. No production or staging data or keys were accessed. M3 is complete only for the disposable implementation scope; live data migration is not complete.

Deliverables:
- Freeze exact source-to-target mapping, migration ordering, destination AAD v2, staging ledger and recovery boundaries.
- Implement fail-closed cryptographic and relationship primitives plus disposable PostgreSQL staging/retry/rollback tests.
- Live schema and source-to-target runner are not in the current authorized scope. Reopen only with a separately approved migration and recovery plan; until then, preserve all legacy tables and runtime domain code.
- Disposable PostgreSQL snapshot migration tests.
- Before/after row counts, FK integrity, owner consistency, ciphertext authentication/decryptability and resume/approval journey checks.
- Quarantine path for owner mismatches, orphaned records and undecryptable payloads.
- Explicit cutover, recovery window and rollback runbook.

Acceptance:
- Upgrade and recovery are repeatable on disposable snapshots.
- Every source row reconciles to verified target, quarantine or approved retention exclusion.
- Source records remain intact until the recovery window is approved and complete.
- No production/staging migration runs without separate explicit authorization.

### M4 — Remove obsolete runtime code and perform final audit

**Status:** Blocked on successful M3 migration and recovery approval

Deliverables:
- Remove superseded case-domain runtime modules, imports, compatibility code, dead tests and obsolete active runbooks.
- Repository-wide scan of case/demo routes, names, environment variables, imports, customer copy and migration references.
- Classify historical Alembic migrations and research records as retained provenance, not active runtime dependencies.
- Run backend, frontend, browser, PostgreSQL migration, owner-isolation, negative-route, encryption and recovery suites.

Acceptance:
- No active runtime dependency on the old case domain remains.
- Frontend calls only the canonical conversation/task contract.
- Historical migration records remain where required for reproducibility.
- Active documentation and tests accurately describe the final model.

## 5. Verified source dependencies to preserve

The current dependency inventory is maintained in `LEGACY_MIGRATION_PLAN.md`. The critical groups are:

- Task-like case record and confirmed intake facts.
- Thread-to-task association and owner-scoped reconnect/resume.
- Agent run requests, encrypted events and checkpoints.
- Operation/proposal/approval receipts and idempotency/revision constraints.
- Private document vault records, consent, expiry and encrypted metadata.
- Preparation, document review and bounded guide-history records.
- Worker leases, queued-run claim rules and archive/delete race boundaries.

The current `AgentRunRequest.case_id` may be null. Thread/task association is many-to-many. M2.4 preserves both behaviors in the target contract.

## 6. Non-negotiable safeguards

1. Do not drop tables, delete production records, run destructive SQL or rewrite live ownership as part of code-only cleanup.
2. Do not auto-assign ownerless records or repair owner mismatches by copying another row's owner.
3. Do not change encryption keys, AAD, ciphertext identity or retention behavior without a verified migration and recovery plan.
4. Preserve run history, event order, checkpoints, approval receipts, idempotency, revisions and audit provenance.
5. Preserve archive/restore behavior, explicit deletion semantics and worker/task lock ordering.
6. Do not weaken authentication, owner isolation, source review, user confirmation, privacy or production execution gates.
7. Do not change Vercel settings, quotas, billing, permissions or production aliases.
8. Do not start Phase 5.

## 7. Working protocol

For each bounded item:
1. Inspect current `main`, open PRs, exact branch heads and required CI.
2. Work on an isolated branch and open a focused PR.
3. Keep code changes separate from schema/data migration unless the task explicitly authorizes both.
4. Verify relevant backend, frontend, PostgreSQL and browser checks; report skipped checks honestly.
5. Before merge, re-fetch the PR and use its latest exact head SHA as the merge precondition.
6. After merge, verify the PR state and `main` ref.
7. Update this plan and `ACTIVE_WORK.md`/`PROGRESS.md` when the active task or completion status changes.

## 8. Definition of cleanup completion

Cleanup is complete only when M2.4, M2.5, M3 and M4 have passed their acceptance criteria, all remaining case-named artifacts are classified as either intentionally retained historical provenance or removed active dependencies, and the repository's required tests prove ownership, encryption, retention, recovery and conversation/task behavior. A clean search result alone is not sufficient.
