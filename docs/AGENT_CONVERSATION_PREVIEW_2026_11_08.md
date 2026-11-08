# 8 November 2026 — Encrypted conversation history for synthetic agent Preview

## What is implemented

- An **additive** Alembic revision `20261108_0012` adds
  `case_agent_turns` with case ID, owner subject, encrypted turn content,
  a SHA-256 content checksum, and creation timestamp.
- The existing `POST /api/v1/cases/{id}/preparation/guide` saves a successful
  guide question plus bounded, server-produced status/action/answer **only when**
  `ENABLE_AGENT_HISTORY_API=1`. No raw documents, PDF text, complete case
  facts, citations, tool credentials, or full model traces are stored.
- `GET /api/v1/cases/{id}/preparation/conversation` returns up to the latest
  20 turns, with `historical_only=true`. A prior answer is not reinterpreted
  as current legal guidance. The UI optionally displays these prior turns.
- The optional LLM tool selector receives no more than three prior
  **user questions and action labels**, marked untrusted. The deterministic
  rules engine and case facts continue to load fresh on every request.
- Deleting the case deletes its conversation, with both service-layer cleanup
  for SQLite fixtures and `ON DELETE CASCADE` in PostgreSQL.
- Encryption uses the existing **separate Preview-only 256-bit AES-GCM
  document key**, with case ID, owner subject, and turn ID bound as
  associated data. Key loss makes the records unreadable.

## Activation constraints

The feature is **off by default** and is forbidden in production through the
existing preparation Preview gate.

1. On an explicitly authorized isolated synthetic-only Preview database,
   review and apply migration `20261108_0012`. This PR does not execute that
   migration on Neon, Vercel, or production.
2. Enable `ENABLE_PREPARATION_API=1` with existing isolated Preview controls.
3. Only after the isolated database revision is verified, opt in to
   `ENABLE_AGENT_HISTORY_API=1` **on the isolated backend Preview only**.
4. The frontend already treats a missing/disabled conversation endpoint
   as an optional feature. Production and existing schema-0011 environments
   continue working without this flag.

The startup guard accepts existing preparation schema `0011` (no history)
or new schema `0012`; it **rejects** history activation against `0011`.

## Limits and remaining work

This provides saved conversation messages and resumable case context, **not**
a fully resumable LangGraph checkpoint of an interrupted tool execution.
The existing read-only graph is short-running and stateless per HTTP request.
For an MVP, a returning user can inspect the saved conversation, and the
guide re-evaluates the current confirmed case facts and reviewed rules.

Do not treat stored text as verified evidence, confirmed user facts, or a
source of rules. No automatic applications or government submissions occur.
Use synthetic data only. A real-data feature needs separate privacy,
retention, deletion, model-provider, and operational review.

Next incremental tasks: add durable agent-run checkpoints if long-running
tool execution becomes necessary; integrate safe conversational RAG
explanations; run a real LLM-backed synthetic end-to-end workflow.

## Verification

Backend CI runs synthetic SQLite tests for auth, tenant isolation, encryption,
pruning, saved-state resumption, disabled-default behavior, and case deletion.
Disposable PostgreSQL CI migrates to `0012` and verifies schema and cascade
behavior. Frontend CI covers TypeScript, build, and local HTTP smoke.

No live Auth0, model-provider, Vercel, or Neon staging execution is asserted.
The master roadmap's unresolved reconciliation gate is unchanged.
