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

1. Point a preview backend to **Neon isolated staging**, migrated to
   `20261105_0009`; never connect review to the production DB.
2. Configure existing Auth0 verification variables:
   `AUTH_ISSUER`, `AUTH_AUDIENCE`, `AUTH_JWKS_URL`.
3. Set backend preview `ENABLE_DEMO_CASE_API=1`,
   `ENABLE_KNOWLEDGE_CATALOG_API=1`,
   `ENABLE_KNOWLEDGE_REVIEW_API=1` and
   `KNOWLEDGE_REVIEWER_SUBJECTS=<verified Auth0 subject(s)>`.
   Obtain subjects from verified Auth0 identity, **not from a typed email
   address or unauthenticated claim**.
4. Configure the frontend preview's Auth0 server settings,
   `BACKEND_API_URL` pointing to that preview backend, and
   `ENABLE_REVIEW_UI=1`.
5. Open `/knowledge/review` on a phone, sign in as an allowlisted
   reviewer, inspect the excerpts and linked official pages, select the
   reviewed articles, enter a rationale and explicitly attest correctness
   before submitting the batch. This is not a blind approval control.
6. Verify each `knowledge_review_events` record contains the correct
   authenticated actor subject, source hash and review reason.

Do not set preview review flags on Vercel production; deployment and live
Auth0 round-trip have not yet been verified. When Vercel deployment limits
prevent a fresh preview, the UI remains untested live even if CI succeeds.

## Content scope

The staging batch has 12 Comune di Milano FAQ captures with page dates
ranging from 2025–2026. The queue is not proof they are currently legally
applicable. Review the exact text and any newer conflicting municipal forms.
The 2013 historical Allegato A remains pending for independent verification.
The two initially open source pages were not in the 12-record capture batch.

The user requested bulk approval in chat. That is a **product request and
instruction to assist**, not an Auth0 reviewer login. Neither this tool nor
the assistant should fabricate a verified reviewer identity or create
fake approval audit entries directly in SQL.
