# Authenticated RAG Q&A preview

**Status:** development feature behind disabled-by-default flags. No production
RAG endpoint or official administrative advice is enabled.

## What is implemented

- A case-bound FastAPI route, `POST /api/v1/cases/{case_id}/assistant/ask`,
  protected by the existing Auth0 RS256 bearer-token verifier.
- Case ownership checks: another user's case returns 404. The request cannot
  choose a jurisdiction, source approval status, or administrative procedure.
- Fixed initial evidence scope: `IT-MI-MILANO`,
  `milan_residence_change`, source language `it`.
- Search over active, individually approved and revalidated passages only.
  For now the endpoint uses the lexical fallback of the hybrid retriever;
  semantic search requires separately approved embeddings and a tested
  embedding provider.
- No matching approved evidence -> `insufficient_evidence` and **zero model
  calls**. With no configured model and some approved evidence ->
  `model_not_configured`. Provider failures -> `generation_unavailable`.
- When approved evidence **and** an explicitly configured model are available,
  LangChain calls ChatOpenAI with short output and timeout limits. Responses
  without valid in-bundle citation IDs are withheld as
  `unverified_answer`. This mechanical filter **does not verify that each
  generated factual claim is supported**; further evaluation is required.
- A bilingual, case-linked preview page under
  `/cases/{case_id}/assistant`, plus an authenticated same-origin Next.js
  proxy. User input is not saved as chat history.
- Synthetic-only tests for authentication, isolation, source approval,
  citation rejection, revocation and model failures.

## Example request (requires a real authenticated preview case)

```http
POST /api/v1/cases/123e4567-e89b-12d3-a456-426614174000/assistant/ask
Authorization: Bearer <JWT>
Content-Type: application/json

{"question":"residenza","language":"it"}
```

The backend rejects unauthorized cases, unknown procedure context, queries
over 180 characters and queries with more than 12 searchable terms. The
frontend proxy also requires an exact same-origin Origin header and allows
only `question` and `language`.

## Flags — all off by default

Backend **preview/development only**:
- `ENABLE_DEMO_CASE_API=1`
- `ENABLE_KNOWLEDGE_CATALOG_API=1`
- `ENABLE_KNOWLEDGE_SEARCH_API=1`
- `ENABLE_ASSISTANT_API=1`
- `DATABASE_URL` pointing **only to the migrated, isolated staging branch**
- Trusted `AUTH_ISSUER`, `AUTH_AUDIENCE`, `AUTH_JWKS_URL`

Frontend **preview/development only**:
- `ENABLE_ASSISTANT_UI=1`
- Existing Auth0 server-side variables and `BACKEND_API_URL` pointing to
  the isolated preview backend.

Both Vercel `production` environments are explicitly excluded in code.
The frontend guard requires `VERCEL_ENV=preview` or local development.
The backend refuses startup when `ENABLE_ASSISTANT_API=1` and
`VERCEL_ENV=production`. Do not set the preview flags in Production.

**Optional model:** `ASSISTANT_CHAT_MODEL` and `OPENAI_API_KEY` are used
*only after approved evidence is retrieved*. Both must be provided securely
by the operator. Neither is set by this PR. ChatOpenAI uses a 15-second
timeout, no retry, and at most 500 generated tokens. Do not enable external
model calls until a provider privacy review, safety evaluation, usage
monitoring and per-user rate limits exist. Never commit credentials.

## Current staging reality

Neon staging had 17 candidate sources and one older Allegato A PDF marked
`pending_review`, **zero approved sources** and **zero embeddings** at the
time of this milestone. Therefore every legitimate live question must
return `insufficient_evidence`, regardless of any configured AI model.
The deterministic tests create and approve **fictional** HTML inside a
disposable SQLite database; they do not approve real municipal evidence.
Never approve the historical PDF merely to make a demo answer appear.

## Release blockers / remaining work

1. Acquire and independently approve **current** original municipal sources.
2. Select and evaluate a 1,536-dimensional embedding model and controlled
   indexing of exact approved passages.
3. Add multilingual retrieval evaluation for English questions against
   Italian documents; the first endpoint currently searches Italian text
   using keyword matching.
4. Add rigorous claim-level citation verification, prompt injection
   evaluation, privacy controls and distributed per-user rate limiting.
5. Test authenticated case UI through a real preview browser with configured
   Auth0 and staging backend; unit/CI success alone does not establish that
   live end-to-end authentication is operational.
6. Complete deterministic administrative rules before guiding users on
   eligibility, mandatory forms or deadlines.

**Do not release to production until these gates are met.**
