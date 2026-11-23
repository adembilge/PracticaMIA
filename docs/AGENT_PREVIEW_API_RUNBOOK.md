# Phase 4 — Isolated agent API Preview mount

**Status:** Code and offline/CI smoke coverage only. This is not a live Auth0, worker or government-source validation, and it does not start Phase 5.

## Scope

The ordinary FastAPI application now *can* mount the existing encrypted `/api/v1/agent/*` transport. It stays **absent unless every guard passes**. Its role is to durably accept the first natural-language message, return owner-scoped conversation history, retrieve status and questions, and record verified replies/approvals. The frontend Preview BFF at `/api/agent/*` retains Auth0 and CSRF checks, and intentionally does **not** forward the internal `/threads/{id}/cases` route.

### Exact activation conditions (all required)

- API deployment: `VERCEL_ENV=preview`, on `VERCEL_GIT_COMMIT_REF=preview/auth-review-isolated` only. Do **not** set these flags on production, on PR branches, or on unrelated previews.
- Set `ENABLE_AGENT_PREVIEW_API=1` only for the reviewed isolated API Preview.
- Also enable existing staging flags: `ENABLE_TASK_API=1`, `ENABLE_KNOWLEDGE_CATALOG_API=1`, `ENABLE_PREPARATION_API=1`, `ENABLE_AGENT_HISTORY_API=1`, and `PREPARATION_TARGET=isolated_staging`.
- `DATABASE_URL` must point to reviewed isolated PostgreSQL (never production, pooler redirection or SQLite). `PREPARATION_DATABASE_FINGERPRINT` must equal SHA-256 of the **exact connection URL**, already inspected for direct Preview target and credentials, without printing or committing the URL.
- `AGENT_PREVIEW_JOURNAL_KEY`: a dedicated, random 32-byte key encoded as standard base64. Generate in an approved secret-management environment. It **must differ** from `PREPARATION_DOCUMENT_KEY`. Do not rotate either key while existing encrypted test conversations need to remain recoverable; plan and verify re-encryption/retention first.
- Valid Auth0 issuer, audience and JWKS configuration. Verify both reviewer and ordinary test accounts under the intended Preview tenant.
- Database migration revision must pass the existing staging schema guard before any route is mounted.

If any requirement fails, FastAPI startup raises and does **not** expose the agent route. Without `ENABLE_AGENT_PREVIEW_API`, the same endpoints stay 404.

## Phase 4 case-free LangGraph worker (code available; not deployed)

`backend/app/agent/chat_graph.py` now compiles a real LangGraph execution graph with bounded nodes for:

1. Load the authenticated conversation message and encrypted checkpoint
2. Identify intent and exact procedure/location candidates from the active pilot vocabulary
3. Ask an in-chat municipality clarification and resume the same run from its recorded reply
4. Retrieve only active, human-approved passages for the explicitly matched Milan residence-change scope
5. Revalidate exact source versions and publish **reference-only** citations

The worker is deliberately **case-free**:

- It accepts only messages with `case_id=None`.
- The one-shot worker claims only unlinked conversation runs (`unlinked_only=True`); it cannot consume or finalize legacy case-linked queue entries.
- Location candidates are stored in the encrypted checkpoint so a municipality clarification can resume without creating or selecting a case.
- Pilot aliases are enabled only while the exact reviewed Milan source passage is active. Retrieval and publication independently re-check source approval, version and hash.
- With no personal task-scope assignment and no claim review, the graph can show exact official source cards as general references, but it cannot publish a legal conclusion, official channel, deadline or personalized requirement.
- The graph now has an optional case-free model reference selector, **disabled by default**. It requires both `ENABLE_CASE_FREE_AGENT_MODEL=1` and `ASSISTANT_MODEL_PRIVACY_APPROVED=1`, the exact isolated Preview branch, a configured provider and the keyed usage hash. No environment flag has been enabled by this code change.
- The selector reserves the existing pseudonymous per-user daily quota before a provider call. It sends only a bounded topic category and excerpts from already-approved public passages; it never sends the raw user message, Auth0 subject or private case data.
- The model can return only exact candidate passage IDs. The server rejects unknown, duplicate or malformed IDs. The model cannot generate answer prose, claims, legal applicability, source approval, official channels or actions. The final chat result remains explicitly reference-only with no claims or official channel.
- With either privacy gate disabled, missing configuration, exhausted quota or provider failure, the graph falls back to its deterministic reference-only behavior. The selector is not a production assistant and does not validate administrative rules.
- No documents are processed, no facts are written, no external portal is called, and no government action is submitted.

The worker still uses the existing durable database lease, encrypted event journal, checkpoint revision and stale-worker fencing. It is manually invoked, one-shot, and capped at 1–20 worker attempts. The optional model selector is invoked only inside the same bounded step and only behind the gates above. The worker is **not a Vercel background service or scheduler**.

**Optional manual command in a reviewed isolated execution environment** (not executed by this PR):

```bash
cd backend
python -m app.agent.preview_worker --once --unverified-only --max-steps 8
```

The expected output is a committed-step count only. It omits prompts, owner IDs, private data, tokens, keys and connection strings. CI exercises a disposable approved-source registry, case-free queue execution, two-language clarification/resumption, owner-scoped source cards, citation withdrawal and the PostgreSQL transport. This is not a live Auth0 run or proof that the deployed Preview is configured.

**Next dependency:** Derive and confirm the narrow pilot facts inside the conversation, then connect them to independently reviewed service-area assignments and claim reviews. Only after those gates should a separate claim-safe answer-generation step be considered. Add bounded hosted scheduling/monitoring and real two-account Preview acceptance separately. Do not enable full execution while source, privacy and tenant gates are pending.
## Optional case-free model reference selector

The adapter in `backend/app/agent/model_adapter.py` is code-only and default-off. Its two independent flags are:

- `ENABLE_CASE_FREE_AGENT_MODEL=1`
- `ASSISTANT_MODEL_PRIVACY_APPROVED=1`

It additionally requires `VERCEL_ENV=preview`, `VERCEL_GIT_COMMIT_REF=preview/auth-review-isolated`, a configured OpenAI model or OpenRouter free model, a 32-character usage-hash key and a daily limit from 1 to 50. The per-user subject is supplied transiently by the authenticated worker and stored only as a keyed digest in `assistant_daily_usage`. The user message is not passed to the model; a fixed category label is used instead. The adapter can only narrow an already-approved candidate set. Any failure falls back to deterministic reference-only output. Do not enable these flags until the privacy review and provider-processing terms are approved for the isolated Preview.

## Remaining boundary: no autonomous or LLM-backed worker deployment

The endpoint returns `202 Accepted` for a successfully persisted, encrypted user message, **not an answer**. The manual case-free LangGraph worker can advance unlinked Preview runs to a clarification or reference-only result. A model call is possible only when both explicit privacy flags, exact Preview branch, provider configuration and daily quota checks pass; it selects source IDs only and does not publish personalized verified guidance. No background worker is started in a serverless request and the frontend must not present queued as completed. A dedicated worker deployment and external scheduling/retry policy remain separate tasks.

Do not enable a real-model executor by pointing a general agent to unapproved official material. The isolated CI suite uses deterministic fictional sources; its 4/4 PR success is not legal, factual or participant validation.

## Verification and rollout order

1. Inspect the target API Preview service, Git SHA, Vercel protected branch and **Neon database branch ID**. Ensure the connection fingerprint is correct and distinct from production. Never modify the production DB branch.
2. Run backend tests plus the migrated disposable PostgreSQL smoke `tests/test_postgres_agent_preview_mount.py`, case-free graph tests in `tests/test_agent_chat_graph.py`, and selector contract tests in `tests/test_agent_model_adapter.py`; verify owner-only history, no plaintext message, clarification/resumption, per-user quota reservation, privacy gates, exact candidate-ID validation and reference-only citations. The PostgreSQL smoke deliberately returns no approved passages, so it must not fabricate an answer.
3. Independently configure the reviewed Preview API secret and flags, then deploy **that exact reviewed commit to the isolated Preview branch**. Verify route presence via OpenAPI and 401 anonymous access; if service deployment fails, record it rather than bypassing protection.
4. Deploy the same reviewed commit to the separate Preview web app with `ENABLE_SINGLE_CHAT_PREVIEW=1` and configured `BACKEND_API_URL`; verify first-message acceptance using two signed-in test accounts, with B denied A history.
5. **Do not sign off as a usable assistant** until the conversation graph can answer the user's actual question with a sourced or explicitly uncertain explanation, keep personal claims behind reviewed scope, and retain history across reloads. The current model selector only narrows reference cards.
6. Before any public release, finish source/human review, worker observability, retry/dead-letter policy, privacy and data retention gates, real-document upload controls, legacy data migration and hosted one-route E2E. Keep Phase 5 on hold until explicitly authorised.

No new Vercel environment variables have been set by the repository PR. No Preview/production deployment or real personal user messages have been initiated by this code change.
