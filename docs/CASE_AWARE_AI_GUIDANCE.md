# Saved-case-aware AI guidance (first Milan MVP route)

## Purpose

Give a signed-in user clear navigation based on their **actual five persisted scope
answers**, instead of the old fixed-fictional-topic OpenRouter demonstration.
The case backend remains the authority for which account owns a case.

## Flow

1. The client displays a deterministic, case-specific next action from the
   saved answers, without making any AI request.
2. On an explicit click, the browser POSTs **only** `topic` and `language`
   to `/api/cases/{id}/guidance` on the same origin.
3. The Next.js server checks Origin, UUID, strict request shape, and a
   production-only feature gate, then fetches the case via the existing
   server-side Auth0 access token and owner-filtered case backend.
4. The server validates the case ID, procedure, five-answer shape, and
   consistency between the saved status and product scope classifier.
5. The server generates deterministic, localized `summary` and `next_step`.
6. OpenRouter receives **only a derived abstract workflow status and the
   index of the next product question**, not any raw yes/no answers, UUID,
   account identity, address, document, or chat input.
7. The AI response is displayed separately and labeled as an unverified
   explanation. Missing, failed or rejected AI responses do not remove the
   deterministic next action. Every response is non-cacheable.
8. Editing a case question invalidates earlier AI output in the UI.

## Explicit limitations

- **These are product scope decisions, not Italian legal eligibility rules.**
- The five saved questions do **not** establish Italian citizenship, whether
  a rental contract is registered, or which documents are required.
- No personalized proof substitutions, legal deadlines, identity checks,
  official portal submission or government approval is claimed.
- Current approved-source provenance remains visible in the separately
  authenticated `ReviewedSourcesPanel`. The historical ANPR guide is
  explicitly labeled as archived, not guaranteed current.
- Real address, lease, move-in-date and identity fields are not currently
  stored in the saved-case core. A future audited intake model will be
  needed before the assistant can safely guide on those details.
- OpenRouter free models can return irrelevant or inaccurate explanations.
  The hard-coded workflow next action must be treated as the product's
  controlled result; AI text never authorizes actions.

## Release and testing

- No new database migration or Vercel environment variable is necessary.
  The new endpoint uses existing production `OPENROUTER_API_KEY`,
  `ENABLE_PUBLIC_SYNTHETIC_AI`, `BACKEND_API_URL`, and Auth0 settings.
- `frontend/tests/case-guidance.test.mjs` tests saved-answer statuses,
  uncertain and unsupported paths, strict body shape, ID validation, and
  that model prompts exclude raw case data.
- Frontend GitHub CI should run `npm test`, `npm run typecheck`,
  and `npm run build`.
- **Do not build or deploy via Vercel for this development task.**
  Existing Vercel-GitHub integration may still report blocked deployments
  due to the quota; it is not a substitute for GitHub CI.
- Before live activation, verify Auth0 sign-in, case ownership, edit
  invalidation, provider failure fallback, and no user data in outbound
  OpenRouter requests in a controlled end-to-end test.
