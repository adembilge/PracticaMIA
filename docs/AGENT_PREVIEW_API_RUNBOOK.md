# Phase 4 — Isolated agent API Preview mount

**Status:** Code and offline/CI smoke coverage only. This is not a live Auth0, worker or government-source validation, and it does not start Phase 5.

## Scope

The ordinary FastAPI application now *can* mount the existing encrypted `/api/v1/agent/*` transport. It stays **absent unless every guard passes**. Its role is to durably accept the first natural-language message, return owner-scoped conversation history, retrieve status and questions, and record verified replies/approvals. The frontend Preview BFF at `/api/agent/*` retains Auth0 and CSRF checks, and intentionally does **not** forward the internal `/threads/{id}/cases` route.

### Exact activation conditions (all required)

- API deployment: `VERCEL_ENV=preview`, on `VERCEL_GIT_COMMIT_REF=preview/auth-review-isolated` only. Do **not** set these flags on production, on PR branches, or on unrelated previews.
- Set `ENABLE_AGENT_PREVIEW_API=1` only for the reviewed isolated API Preview.
- Also enable existing staging flags: `ENABLE_DEMO_CASE_API=1`, `ENABLE_KNOWLEDGE_CATALOG_API=1`, `ENABLE_PREPARATION_API=1`, `ENABLE_AGENT_HISTORY_API=1`, and `PREPARATION_TARGET=isolated_staging`.
- `DATABASE_URL` must point to reviewed isolated PostgreSQL (never production, pooler redirection or SQLite). `PREPARATION_DATABASE_FINGERPRINT` must equal SHA-256 of the **exact connection URL**, already inspected for direct Preview target and credentials, without printing or committing the URL.
- `AGENT_PREVIEW_JOURNAL_KEY`: a dedicated, random 32-byte key encoded as standard base64. Generate in an approved secret-management environment. It **must differ** from `PREPARATION_DOCUMENT_KEY`. Do not rotate either key while existing encrypted test conversations need to remain recoverable; plan and verify re-encryption/retention first.
- Valid Auth0 issuer, audience and JWKS configuration. Verify both reviewer and ordinary test accounts under the intended Preview tenant.
- Database migration revision must pass the existing staging schema guard before any route is mounted.

If any requirement fails, FastAPI startup raises and does **not** expose the agent route. Without `ENABLE_AGENT_PREVIEW_API`, the same endpoints stay 404.

## Current backend boundary: no agent worker yet

The endpoint returns `202 Accepted` for a successfully persisted, encrypted user message, **not a generated answer**. A runnable agent must advance the `queued` request using the already implemented lease/fenced `run_worker_batch` service, a permitted execution adapter, and reviewed source scope. No background worker is started in a serverless request and the frontend must not present queued as completed. A dedicated worker deployment and external scheduling/retry policy are still separate tasks.

Do not enable a real-model executor by pointing a general agent to unapproved official material. The isolated CI suite uses deterministic fictional sources; its 4/4 PR success is not legal, factual or participant validation.

## Verification and rollout order

1. Inspect the target API Preview service, Git SHA, Vercel protected branch and **Neon database branch ID**. Ensure the connection fingerprint is correct and distinct from production. Never modify the production DB branch.
2. Run backend tests plus the migrated disposable PostgreSQL smoke `tests/test_postgres_agent_preview_mount.py`; it verifies owner-only history and no plaintext message, while the queued run has no fabricated response.
3. Independently configure the reviewed Preview API secret and flags, then deploy **that exact reviewed commit to the isolated Preview branch**. Verify route presence via OpenAPI and 401 anonymous access; if service deployment fails, record it rather than bypassing protection.
4. Deploy the same reviewed commit to the separate Preview web app with `ENABLE_SINGLE_CHAT_PREVIEW=1` and configured `BACKEND_API_URL`; verify first-message acceptance using two signed-in test accounts, with B denied A history.
5. **Do not sign off as a usable assistant** until the separately developed worker can process queued requests, return an actual sourced or explicitly uncertain answer, and retain history across reloads.
6. Before any public release, finish source/human review, worker observability, retry/dead-letter policy, privacy and data retention gates, real-document upload controls, legacy data migration and hosted one-route E2E. Keep Phase 5 on hold until explicitly authorised.

No new Vercel environment variables have been set by the repository PR. No Preview/production deployment or real personal user messages have been initiated by this code change.
