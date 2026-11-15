# Saved-case-aware AI guidance (first Milan MVP route)

## Purpose

Give a signed-in user clear navigation based on their **actual five persisted scope
answers**, with an optional OpenRouter explanation.
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
- The [structured intake](STRUCTURED_CASE_INTAKE.md) stores categorical facts and an optional move date. This guidance endpoint classifies the five scope answers and sends only the bounded derived context described above.
- OpenRouter free models can return irrelevant or inaccurate explanations.
  The hard-coded workflow next action must be treated as the product's
  controlled result; AI text never authorizes actions.

## Authenticated Preview chat

The case assistant at `/cases/{id}/assistant` is a separate, Preview/development-gated chat. It accepts bounded EN/IT questions through `POST /api/cases/{id}/assistant/ask`. The backend checks case ownership and uses active reviewed Italian passages, a narrow English term fallback, and exact quote verification. Unsupported questions, unavailable providers and unverified output have explicit fallback states. Optional synthetic preparation guidance and encrypted history have independent flags.

Use `ENABLE_ASSISTANT_UI` on the frontend and the backend case, catalog, search and assistant settings documented in [the backend configuration](../backend/app/config.py). Review model input processing and provider terms before expanding access. See [retrieval evaluation](RETRIEVAL_EVALUATION.md) for the bilingual acceptance gap.

## Release and testing

- The endpoint needs no additional schema. It uses the production `OPENROUTER_API_KEY`,
  `ENABLE_PUBLIC_SYNTHETIC_AI`, `BACKEND_API_URL`, and Auth0 settings.
- `frontend/tests/case-guidance.test.mjs` tests saved-answer statuses,
  uncertain and unsupported paths, strict body shape, ID validation, and
  that model prompts exclude raw case data.
- Frontend GitHub CI should run `npm test`, `npm run typecheck`,
  and `npm run build`.
- Use [progress and blockers](PROGRESS.md) for hosted evidence. Cover Auth0 sign-in, case ownership, edit invalidation, provider failure fallback, and the outbound prompt boundary in controlled tests. Conversational Preview retrieval is a separate feature.
