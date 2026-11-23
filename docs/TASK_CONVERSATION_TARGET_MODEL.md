# Conversation/task target data model — M2.4 design draft

**Status:** Draft for engineering review; no schema change authorized  
**Date:** 23 November 2026  
**Source inventory:** \`docs/LEGACY_MIGRATION_PLAN.md\` and current SQLAlchemy models on \`main\` at \`82a277c23cca89f655b5bc1e4e11f7089c315c70\`.

## 1. Purpose

Define the target ownership and relationship model before renaming or migrating the existing case domain. This is a design artifact, not an implementation or migration approval.

The target concepts are:
- **Conversation:** persistent customer chat and its owner.
- **Task:** private workflow context associated with a conversation.
- **Confirmed intake:** user-entered and explicitly confirmed facts, separate from provisional scope answers.
- **Evidence and preparation:** private documents, extraction, review and preparation state.
- **Agent execution:** durable runs, ordered events, resumable checkpoints and approval receipts.

No customer-facing task picker, task dashboard or standalone task page is introduced.

## 2. Current source-to-target mapping

Target names are proposals. Existing tables remain authoritative until a separately reviewed data migration is approved.

| Current source | Current responsibility | Proposed target | Migration notes |
|---|---|---|---|
| \`agent_threads\` / \`AgentThread\` | Conversation identity, owner, revision | \`conversations\` | Preserve ID, owner and revision |
| \`cases\` / \`CaseRecord\` | Task identity, owner, procedure, status, scope answers, archive and timestamps | \`tasks\` | Preserve IDs and timestamps; nullable owner remains unassigned/inaccessible |
| \`case_intakes\` / \`CaseIntake\` | Confirmed facts, checklist progress/fingerprint and confirmation time | \`task_intakes\` | Keep provisional scope answers distinct from confirmed facts |
| \`agent_thread_cases\` / \`AgentThreadCase\` | Conversation↔task association | \`conversation_tasks\` | Preserve composite identity and many-to-many cardinality unless separately approved |
| \`agent_run_requests\` / \`AgentRunRequest\` | Durable message run, status, accepted revision, lease, nullable case link | \`conversation_runs\` | Rename case link to nullable task link; preserve exact conversation/task association constraint |
| \`agent_run_events\` / \`AgentRunEvent\` | Ordered encrypted event journal | \`conversation_run_events\` | Keep run/event-sequence identity; re-encrypt if task identity changes in AAD |
| \`agent_run_checkpoints\` / \`AgentRunCheckpoint\` | Encrypted resumable state and event watermark | \`conversation_run_checkpoints\` | Keep one checkpoint per run, revision and watermark |
| \`agent_case_operations\` / \`AgentCaseOperation\` | Transactional approval/idempotency/revision receipt | \`task_operation_receipts\` | Preserve all unique constraints and receipt links |
| \`private_case_documents\` / \`PrivateCaseDocument\` | Encrypted vault uploads, consent, scan and expiry metadata | \`private_task_documents\` | Preserve document ID, owner, consent, scan and 7-day expiry policy |
| \`case_preparations\` / \`CasePreparation\` | Encrypted preparation facts and review digest | \`task_preparations\` | Re-encrypt ciphertext under destination AAD |
| \`case_documents\` / \`CaseDocument\` | Encrypted preparation document and review payload | \`task_documents\` | Preserve ID, checksum, types and ciphertext integrity |
| \`case_agent_turns\` / \`CaseAgentTurn\` | Bounded encrypted guide history | \`task_guide_turns\` | Preserve ordering, checksum and evidence revalidation |

Knowledge/source registry tables are outside this case-domain rename.

## 3. Relationship and cardinality contract

The proposed compatibility baseline is:

| Relationship | Required cardinality | Required behavior |
|---|---|---|
| Conversation → runs | One-to-many | Preserve all historical runs and status transitions |
| Conversation ↔ task | Many-to-many | Do not silently collapse to one-to-one |
| Task → intake | Zero-or-one | One current confirmed intake per task |
| Task → preparation | Zero-or-one | One current encrypted preparation state |
| Task → private documents | Zero-to-many | Independent IDs and expiry metadata |
| Task → preparation documents | Zero-to-many | Preserve independent review payloads |
| Task → guide turns | Zero-to-many | Bounded history, not authoritative checkpoint |
| Conversation run → task | Zero-or-one | Null task link remains valid for unlinked chat runs |
| Run → events | Zero-to-many | Strictly ordered sequence |
| Run → checkpoint | Zero-or-one | Watermark must match event journal |
| Run/task → operation receipts | Zero-to-many | Preserve idempotency and revision uniqueness |

A linked run must reference a task linked to the same conversation. Preserve an equivalent composite relationship between the conversation/task association and the run. A simple FK to the task row is insufficient. A run with a null task link must not be forced into a synthetic task.

## 4. Ownership contract

- Conversation owner is authoritative for conversation and run records.
- Task owner is authoritative for task-scoped records.
- Ownerless legacy task rows remain null, unassigned and inaccessible. Never infer or auto-assign an owner.
- Every task child with a denormalized owner must satisfy child owner equals task owner. Report mismatches and quarantine them; never repair by copying an owner.
- A conversation/task association is valid only when both parents belong to the same owner.
- Run ownership remains derived through its conversation. A linked run additionally requires the exact same-owner association.
- Event and checkpoint ownership remains derived through the run and conversation.
- Operation receipts must be bound to both the run and its task.
- Missing, foreign-owner and ownerless task IDs remain indistinguishable at the public API boundary.

**Review option:** Consider composite owner-aware FKs for task children to enforce owner equality in PostgreSQL. This is not an approved schema requirement; evaluate nullable legacy owners, SQLite test parity and migration lock/cost before selecting it.

## 5. Lifecycle and deletion contract

| Operation | Proposed target behavior |
|---|---|
| Archive task | Retain rows and ciphertext; owner can read; block task mutations and new linked runs |
| Restore task | Re-enable supported writes; preserve existing facts and documents |
| Delete task | Explicit owner-authorized destructive operation; review cascade scope |
| Expire private document | Purge only eligible expired rows through authorized retention path |
| Delete conversation | Explicitly decide whether linked tasks detach, remain or delete; never inherit a destructive cascade accidentally |
| Delete run | Preserve existing event/checkpoint cleanup only where run deletion is explicitly authorized |

Current task deletion cascades through task-bound records and linked runs. Whether this remains the long-term policy is open for review. Private-document retention and database backup/PITR expiry are separate; logical deletion does not mean immediate backup removal.

Archive/restore race guarantees from PR #265 remain mandatory: mutations and worker commits serialize using task-before-run lock ordering; an in-flight result must not commit after archive/delete wins.

## 6. Encryption and AAD identity contract

| Payload class | Current authenticated identity dimensions |
|---|---|
| Agent user message | owner subject, thread ID, run ID, client message ID, case ID, accepted revision |
| Agent event | owner subject, thread ID, run ID, case ID, event sequence |
| Agent checkpoint | owner subject, thread ID, run ID, case ID, checkpoint revision, event sequence |
| Private vault document | case ID, owner subject, document ID |
| Preparation facts/document/review | case ID, owner subject, record-specific identity |

A destination model may use task ID in place of case ID, but migration must:
1. Decrypt using the original key and exact original AAD.
2. Authenticate and validate plaintext in memory.
3. Encrypt using the destination key/version and exact destination AAD.
4. Verify the new ciphertext decrypts and matches expected digest/semantics.
5. Commit identity and ciphertext atomically or through an explicitly recoverable staged protocol.

Never log plaintext. Missing keys, invalid authentication tags, owner mismatches or ambiguous mappings stop and quarantine the row. Do not conflate key rotation and domain migration without independently tested rollback paths.

## 7. Constraints and indexes to preserve

- Unique client message idempotency per conversation.
- One foreground run per conversation where currently enforced.
- Active-run uniqueness per conversation/task pair, including the null-task case.
- Worker lease token/expiry pairing and queue indexes.
- Positive, unique event sequence per run.
- One checkpoint per run, positive revision and nonnegative event watermark.
- Operation uniqueness by run/client operation, run/proposal and task/revision.
- Operation revision equals expected revision plus one.
- Private-document consent version/time, scan time, checksum and expiry metadata.
- Current FK cascade behavior only where explicitly retained in the approved deletion policy.

## 8. Decisions required before schema work

1. Retain many-to-many conversation/task association or constrain one active task per conversation? Current behavior is many-to-many; no evidence authorizes narrowing it.
2. Enforce child/parent owner equality with composite FKs or retain application enforcement plus migration validation?
3. Conversation deletion policy: detach tasks, retain them, or explicit cascade?
4. Task deletion policy: retain explicit cascade or introduce staged purge/tombstone?
5. Legacy ownerless rows: preserve as inaccessible history or quarantine through a separately authorized process? Automatic assignment is prohibited.
6. AAD versioning: use destination task IDs in a new AAD version or retain a versioned compatibility scheme?
7. Confirm proposed physical table names or retain neutral existing names to reduce migration risk.

## 9. M2.4 acceptance checklist

- [x] Current model responsibilities and core source tables inspected.
- [x] Source-to-target entity mapping drafted.
- [x] Conversation/task/run cardinalities and nullable run linkage documented.
- [x] Owner derivation and mismatch handling documented.
- [x] Archive, restore, deletion and retention behaviors documented.
- [x] Encryption/AAD identity requirements documented.
- [x] Important uniqueness, sequence, lease and revision constraints documented.
- [ ] Product/engineering review of the open decisions above.
- [ ] Update \`docs/CLEANUP_PLAN.md\` after review; do not start M2.5 until M2.4 is accepted.

## 10. Explicit non-goals

This draft does not authorize SQLAlchemy or Alembic changes, production/staging data mutation, table/column rename or drop, re-encryption, owner reassignment, retention/deployment changes, production execution-gate changes or Phase 5 work.
