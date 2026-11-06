# PracticaMIA — real authenticated two-account preview acceptance

**Status (6 November 2026): test harness created; LIVE E2E BLOCKED by staging configuration.** This follows the independent audit in PR #31, not a production release or administrative approval.

## Confirmed environment gaps

- Frontend Vercel project has Auth0 identity and session credentials targeted at **production**; the equivalent Preview Auth0 variables are absent.
- Backend Preview configuration is partly bound to the earlier `feature/knowledge-staging-rollout` branch. This is not a coordinated current frontend/backend preview.
- Neon staging has migration `20261106_0010` while production remains on an older schema. Do not point a knowledge/reviewer preview at production.
- The prior single-account Auth0 integration is not a real two-account review and isolation E2E.

## Preconditions for the live run

1. Deploy a dedicated **frontend and backend preview pair** from reviewed code. Backend must use only the isolated Neon staging branch at migration `20261106_0010`. Verify the database identity without printing its connection string.
2. Configure a distinct preview Auth0 Regular Web Application and API, with exact preview callback and logout URLs, RS256 tokens, and matching backend `AUTH_ISSUER`, `AUTH_AUDIENCE`, `AUTH_JWKS_URL`. Do not reuse production Auth0 session credentials.
3. Configure Preview-only frontend Auth0 server variables, `APP_BASE_URL`, and `BACKEND_API_URL`. Set `ENABLE_REVIEW_UI=1` only on preview. Backend preview must enable authenticated cases, knowledge catalog and review routes; add **verified Auth0 subject** of test account A to `KNOWLEDGE_REVIEWER_SUBJECTS`. Account B must not be a reviewer. Keep production review and assistant flags off. The test needs no LLM or embedding key.
4. Create two dedicated synthetic-only Auth0 test accounts using email/password. Do not use real personal data. If MFA, CAPTCHA or a social-only provider prevents automation, report the result as blocked; do not circumvent security.
5. Make the exact preview normally reachable to the authorized CI runner, respecting Vercel Deployment Protection and Auth0 callback policy. Do not bypass those controls.
6. Configure GitHub **environment** `preview-e2e` with two variables: `PRACTICAMIA_E2E_ALLOWED_PREVIEW_HOST` (exact frontend preview hostname, no scheme), `PRACTICAMIA_E2E_AUTH0_HOST` (exact Auth0 tenant hostname ending `.auth0.com`). Configure four environment **secrets**: `PRACTICAMIA_E2E_A_EMAIL`, `PRACTICAMIA_E2E_A_PASSWORD`, `PRACTICAMIA_E2E_B_EMAIL`, `PRACTICAMIA_E2E_B_PASSWORD`. Never put values in this repository or chat.
7. After merging the reviewed PR, run **Actions → Authenticated preview isolation (opt-in) → Run workflow**. Enter the exact `https://<allowed-preview-host>` and explicitly confirm synthetic-only operation. Offline PR tests do not trigger the live browser job.

## What the browser run verifies

- Two distinct real Auth0 sessions and the Next.js-to-FastAPI token bridge.
- Account A creates/updates a synthetic case; B cannot list, read, update, or delete it.
- Account B creates a case; A cannot list or read it.
- Case A remains accessible after page reload.
- Reviewer A can read the review queue; ordinary B is rejected with 403.
- Reviewer A can inspect an integrity-verified *complete captured article*; B cannot.
- Test-created cases are deleted through the owning sessions even if subsequent checks fail.

No official sources are approved, no embeddings are generated, no AI provider is contacted, and no government system is accessed. No credentials, tokens, captured article text, or test-account identifying data are printed. The action uploads sanitized outcome metadata only, retained for 7 days.

## Result interpretation

| Result | Meaning |
| --- | --- |
| **pass** | All real browser authentication, isolation, reviewer and full-text checks passed. |
| **fail** | A functioning preview violated an expected authorization or state assertion. |
| **blocked** | Preview, credentials, identity callback, reviewer route, full-text queue, or access protection unavailable; **not a pass**. |
| **not executed** | PR guardrail tests passed, but no real Auth0 two-account browser test has run. |

The harness is not a physical-mobile usability audit, a screen-reader test, a human source applicability review, or an AI correctness evaluation. After its live pass, perform human review of current municipal evidence, keep the historical source excluded unless validated, then evaluate bilingual retrieval and build deterministic rules and document workflows before user-facing administrative guidance.
