# Mobile browser-source review — preview only

**Status:** An authenticated mobile-friendly approval workflow is implemented,
but not enabled in production. This is a controlled option for a verified
reviewer who cannot conveniently approve 12 source versions one at a time.

## How review works

- `GET /api/v1/knowledge/review/browser-queue` shows the currently pending
  `browser_rendered_text` articles and their SHA-256, official page URL,
  observed last-updated date and a short excerpt.
- `POST /api/v1/knowledge/review/approve-browser-batch` accepts 1–15
  explicitly selected source IDs, version IDs and expected SHA-256 values,
  along with a meaningful review note and a positive attestation.
- The existing **verified Auth0 JWT** and server-side
  `KNOWLEDGE_REVIEWER_SUBJECTS` allowlist are mandatory; an ordinary
  signed-in account and user-supplied role/subject are insufficient.
- Every selected source version must still be pending, latest and
  byte/hash/offset verified. Each is audited under the verified JWT subject.
  All selected sources succeed **in one transaction** or the entire batch
  rolls back.
- The batch operation allows only `browser_rendered_text` snapshots.
  **The historical Allegato A PDF can never be batch-approved.**
- Backend batch approval is explicitly blocked with HTTP 404 when
  `VERCEL_ENV=production`; frontend review UI is also disabled in production.
- Approval does **not** generate embeddings, configure an LLM, or publish
  production guidance. Existing search only consumes individually approved
  and verified source versions.

## Preview-only configuration

1. Point the Preview backend to **isolated Neon staging** at the reviewed deployment’s schema. See [deployment configuration](VERCEL_NEON_DEPLOYMENT.md#isolated-preview).
2. Configure existing Auth0 verification variables:
   `AUTH_ISSUER`, `AUTH_AUDIENCE`, `AUTH_JWKS_URL`.
3. Set backend preview `ENABLE_TASK_API=1`,
   `ENABLE_KNOWLEDGE_CATALOG_API=1`,
   `ENABLE_KNOWLEDGE_REVIEW_API=1` and
   `KNOWLEDGE_REVIEWER_SUBJECTS=<verified Auth0 subject(s)>`.
   Obtain subjects from verified Auth0 identity, **not from a typed email
   address or unauthenticated claim**.
4. Configure the frontend preview's Auth0 server settings,
   `BACKEND_API_URL` pointing to that preview backend, and
   `ENABLE_REVIEW_UI=1`.
5. Open `/knowledge/review` on a phone, sign in as an allowlisted
   reviewer, open the full verified article for each source, compare it with the linked official page, select the articles actually reviewed, then enter a rationale and attest before submitting.
6. Verify each `knowledge_review_events` record contains the correct
   authenticated actor subject, source hash and review reason.

The [hosted case acceptance record](ACCEPTANCE_TESTING.md#manual-staging-case-and-document-checks) covers ordinary case operations. Use the [authenticated Preview runbook](AUTHENTICATED_PREVIEW_E2E_RUNBOOK.md) for reviewer and non-reviewer authorization evidence.

## Content scope

Use the live queue to see pending captures in the selected environment. The [5 November observations](research/BROWSER_OBSERVED_MILANO_RESIDENCE_2026_11_05.md) record the initial source discovery. Review the exact text and check for newer or conflicting official forms before approving a version.
