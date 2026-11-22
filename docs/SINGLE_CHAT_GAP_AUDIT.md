# Single-chat implementation and release gaps

## Implemented in source

- The application root is the single-chat shell.
- Conversation history is the only customer-facing navigation.
- Chat requests use a server-side authenticated proxy with a strict path/query allowlist and same-origin mutation checks.
- Request details required by the current agent are presented inline rather than on a standalone page.
- Human source review remains a separate protected operator surface.

## Removed by the current cleanup

- Standalone customer task/case pages and creation flows.
- Public synthetic demo pages and their browser-only demo engine.
- The editorial landing page and customer account workspace.
- Legacy customer API route groups, except the private request-details adapter required by the in-chat card.

## Still restricted or incomplete

- The agent transport and worker are enabled only in the reviewed isolated Preview environment. Production execution remains disabled.
- The current agent is not an unrestricted, LLM-backed administrative assistant. Its supported behavior is bounded by the Phase 4 graph, approved catalogue and source gates.
- Real personal-document upload/OCR remains disabled pending privacy, malware scanning, key management, retention, backup and operational reviews.
- Live participant validation, current legal/source review, production account-isolation checks and release sign-off remain outstanding.

## Data migration boundary

The backend still uses historical internal task storage and some legacy API/schema names. These are not customer-facing screens. Do not delete or migrate production records in this cleanup. A future storage migration must prove owner mapping, encrypted history continuity, idempotency, retention, rollback and cross-account isolation before any old table or identifier is retired.

## Phase boundary

Phase 4 remains active. The UI consolidation is a cleanup explicitly approved by the product owner; it does not start Phase 5. Phase 5 remains paused.
