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

## Phase 4 bounded worker adapter (code available; not deployed)

`backend/app/agent/preview_worker.py` now provides a **manual, one-shot, strictly capped diagnostic worker**, using the existing `run_worker_batch` lease and encrypted checkpoint/event journal.

- It checks **the same** pinned Preview-branch, PostgreSQL fingerprint, separate 256-bit journal key, migration and Auth0 configuration requirements as the API.
- It requires explicit CLI acknowledgements `--once --unverified-only`; `--max-steps` is limited to 1–20. It never starts a daemon, invokes a remote LLM, submits anything to an authority or modifies a person's data.
- In current **unverified-only** mode, it reads the owner-scoped message, advances a conservative heuristic intent node and records an explicitly unverified response (no legal claims, citations or official handoff). This mode demonstrates queue → leased worker → encrypted history → chat read, **not a ready administrative assistant**.
- A worker crash can leave a lease until expiry; the existing DB fences old writers. Only committed checkpoints can be resumed; never retry with unbounded busy loops.
- Do not run this on a database with real user requests without reviewing the impact: even a diagnostic response finalizes a queued run. This adapter is for synthetic, disposable Preview validation, not participant pilots.

**Optional manually controlled command in a reviewed isolated execution environment** (not executed by this PR):

```bash
cd backend
python -m app.agent.preview_worker --once --unverified-only --max-steps 8
```

The expected output is a **count of committed steps only**. It intentionally omits prompts, subjects, private data, tokens, keys and connection strings. GitHub CI exercises SQLite signed JWT roundtrips and the already-migrated disposable PostgreSQL store, but the runner is **not scheduled**, a separate worker service has not been deployed, and hosted Auth0 two-account tests remain pending.

**Next dependency:** Replace this no-guidance diagnostic adapter with a reviewed-source execution adapter wired into the intended LangGraph nodes, then independently add bounded scheduling/monitoring and real Preview acceptance. Do not activate full execution while official-source and privacy gates are pending.

## Earlier boundary: no autonomous agent worker yet

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
