# Authenticated Preview isolation runbook

The manual staging case walkthrough covered two signed-in accounts, persisted review marks, protected scope and PDF routes, and owner download. See the [hosted staging observations](ACCEPTANCE_TESTING.md#manual-staging-case-and-document-checks). The opt-in GitHub Actions harness below additionally tests reviewer authorization and full-article retrieval. The manual case walkthrough supplies no evidence of a pass for that wider harness.

## Preconditions

1. Use the paired frontend and backend isolated Preview deployments at the same reviewed Git tree. Check the Neon staging branch and migration compatibility against [deployment configuration](VERCEL_NEON_DEPLOYMENT.md).
2. Use a separate Preview Auth0 application and API. Configure the exact callback, logout and frontend origins, and match the backend issuer, RS256 audience and JWKS URL. Keep production credentials out of Preview.
3. On Preview, configure the backend cases, knowledge catalog and review flags and the frontend review UI. Use the verified Auth0 subject of dedicated test account A in the reviewer allowlist. Account B must be an ordinary signed-in account. A pending browser-captured article is necessary to exercise full-text retrieval. An empty queue skips that assertion. The harness needs the isolated synthetic preparation API and UI, with pending rules for its blocked-package assertions. See the [application startup guards](../backend/app/main.py). The default run needs no model or embedding provider. The optional assistant matrix requires the configured staging assistant and provider.
4. Use two synthetic-only Auth0 database accounts. If MFA, CAPTCHA, an unsupported login connection or deployment protection prevents the run, record it as blocked.
5. In the GitHub environment `preview-e2e`, set `PRACTICAMIA_E2E_ALLOWED_PREVIEW_HOST` and `PRACTICAMIA_E2E_AUTH0_HOST` to the exact allowed hostnames. Store `PRACTICAMIA_E2E_A_EMAIL`, `PRACTICAMIA_E2E_A_PASSWORD`, `PRACTICAMIA_E2E_B_EMAIL` and `PRACTICAMIA_E2E_B_PASSWORD` as environment secrets. Never log their values.
6. Run [Authenticated preview isolation (opt-in)](../.github/workflows/authenticated-preview-e2e.yml) from GitHub Actions. Select the exact `https://<allowed-preview-host>` and confirm synthetic-only operation. Select `assistant_matrix` to repeat the 14 staged EN/IT assistant prompts. The audit records fixture IDs, languages, citation counts and pass/fail. The PR check runs offline guardrail tests. The live job requires manual dispatch.

## Assertions and outcomes

- Two distinct Auth0 sessions use the Next.js-to-FastAPI token bridge.
- Account A creates, updates and reloads a synthetic case. Account B cannot list, open, update or delete it. Account A cannot list or open account B's case.
- The owner uploads a generated text-bearing PDF, extracts and confirms a field, and reviews it. Pending rules keep its package blocked. Account B is denied read/write operations on the owner’s preparation and document.
- Reviewer A can open the queue and inspect the integrity-checked full article when a pending capture is present. Ordinary account B is denied. The run never approves sources.
- The harness attempts cleanup through the owning sessions even on failure and saves sanitized outcome metadata for seven days.

Interpret a pass with its completed assertions. An empty queue leaves the full-article check unexercised. Missing reachability, credentials, callbacks, or required routes can block the run. A violated assertion on a functioning Preview is a failure. Source applicability, document processing, model evaluation and physical mobile or assistive-technology usability have their own acceptance evidence.
