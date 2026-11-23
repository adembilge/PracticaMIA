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
- Checklist, workflow and package endpoints: `checklist_router.py`, `workflow_router.py`, `package_router.py`, now mounted only under `/api/v1/conversations/tasks`; the hidden `/api/v1/cases` aliases have been removed.
- Private-document vault, document intelligence, preparation and assistant endpoints are also mounted only under `/api/v1/conversations/tasks`; their hidden `/api/v1/cases` aliases have been removed. Internal `case_id` identifiers and persistence dependencies remain for the later domain/data migration.
- Agent reconnect transport still contains case-linked request/response models and internal thread-to-case link persistence. The former thread task-picker endpoint has been removed; no customer-facing picker is permitted.

### Domain and persistence layer

- `CaseRecord` and `CaseIntake` are still the source of internal task scope and confirmed categorical facts.
- Private-document, preparation, checklist-progress and proposal records reference case IDs.
- `AgentThreadCase` is still read by case-context projection, worker lease ownership checks, run acceptance and approved catalogue evidence. `agent_run_requests` has a composite foreign key to `(agent_thread_cases.thread_id, agent_thread_cases.case_id)`; `agent_case_operations` references both run and case records. These links cannot be removed as dead code.
- `AgentRunRequest.case_id` is included in AES-GCM associated data for encrypted user messages, run events and checkpoints. Renaming or reparenting those records requires an explicit decrypt/re-encrypt migration with key-availability and integrity verification; a column-only rename is insufficient.
- `private_case_documents` ciphertext is bound by associated data containing case ID, owner subject and document ID. `case_preparations` and `case_documents` contain encrypted payloads; deletion or reassignment would invalidate recovery or retention guarantees.
- Alembic history contains case-named tables, constraints and foreign keys. Existing records may include encrypted content and audit-relevant state.

### Dependency graph verified in runtime models

The current SQLAlchemy models and migration history establish the following dependency edges. This is an inventory of live constraints, not a proposal to preserve the old domain permanently.

| Parent | Dependent records | Why the dependency is live |
| --- | --- | --- |
| `cases` | `case_intakes` | Confirmed intake facts, confirmation timestamp and checklist progress |
| `cases` | `agent_thread_cases` | Owner-scoped thread-to-task link used during run acceptance, context projection and resume |
| `agent_threads` + `agent_thread_cases` | `agent_run_requests` | Composite FK binds each linked run to the exact thread/task pair |
| `agent_run_requests` | `agent_run_events`, `agent_run_checkpoints`, `agent_case_operations` | Encrypted event journal, resumable worker state and transactional approval receipts |
| `cases` + `agent_run_requests` | `agent_case_operations` | Approval receipt records the task and run that committed a revision |
| `cases` | `private_case_documents` | Encrypted private uploads, review metadata, consent provenance and expiry |
| `cases` | `case_preparations`, `case_documents`, `case_agent_turns` | Encrypted preparation facts, document/review payloads and bounded guide history |

The regression test `backend/tests/test_case_domain_migration_invariants.py` locks the critical foreign-key edges and verifies that changing the case identity changes the associated-data context for agent messages, events, checkpoints, private documents and preparation payloads.

### Encryption and identity constraints

- Agent request ciphertext associated data includes owner subject, thread ID, run ID, client message ID, case ID and accepted revision.
- Agent event ciphertext associated data includes owner subject, thread ID, run ID, case ID and event sequence.
- Agent checkpoint ciphertext associated data includes owner subject, thread ID, run ID, case ID, checkpoint revision and event sequence.
- Private vault ciphertext associated data includes case ID, owner subject and document ID.
- Synthetic preparation ciphertext associated data includes case ID, owner subject and a record-specific name (for example, `case-facts` or `{document_id}:review`).
- These values are authenticated, not merely descriptive metadata. Updating a foreign key without decrypting and re-encrypting the payload under the destination associated data makes the ciphertext undecryptable.
- Private-vault and preparation keys are separate configuration inputs. A migration must identify and validate the relevant key material for every encrypted record class before it starts; it must not assume that one key can decrypt all payloads.
- Preserve owner subjects exactly. A task migration is not an opportunity to merge owners, infer ownership or broaden access.

### Configuration and documentation

- PR #257 removed the `ENABLE_DEMO_CASE_API` fallback and `enable_demo_case_api` constructor alias. `ENABLE_TASK_API` is the sole supported task-route activation flag and remains disabled by default.
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
- Remove case-selection and thread-to-case linking only after the current run, resume, shared-fact and evidence-scope dependencies have been replaced and regression-tested. The existing links are still operational dependencies, not dead code.
- Keep evidence, proposal, approval and owner authorization invariants intact.
- Retain compatibility adapters only where a verified migration still requires them; do not expose them publicly.

### M2 exit gate — prove the replacement graph before changing storage

Before changing a model, foreign key or table name:

1. Define the target task, conversation, intake, document, preparation, run, event, checkpoint and approval-receipt ownership model, including exact cardinality and deletion semantics.
2. Produce a complete source-to-target mapping for every row in the dependency graph above, including null/legacy-owner rows and records whose parent is archived.
3. Specify how each encrypted payload is read, verified, decrypted and re-encrypted under the destination associated data. Identify key availability, key versioning, failure handling and a no-plaintext logging policy.
4. Preserve run idempotency keys, accepted revisions, event sequence numbers, checkpoint watermarks, approval receipts, timestamps, consent records, expiry dates and audit history.
5. Choose and test a write-consistency strategy (write fence or explicitly designed dual-write). Do not assume dual-write is safe without conflict resolution and replay semantics.
6. Run a dry migration against a disposable PostgreSQL snapshot. Compare row counts, FK integrity, owner boundaries, ciphertext authentication/decryptability and representative resume/approval journeys.
7. Define rollback and recovery before cutover. Keep the source schema and records intact through an approved recovery window; do not drop or cascade-delete source data as part of the first migration.

The new invariant test is a guardrail, not proof that a data migration is ready. It protects known constraints while the complete source-to-target mapping and operational plan are developed.

### M3 — Data migration

- Design Alembic migrations for task tables and all dependent foreign keys only after the M2 exit gate is reviewed.
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
