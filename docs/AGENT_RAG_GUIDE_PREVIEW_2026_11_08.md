# 8 November 2026 — Source-grounded RAG answers in the case guide

## Delivery

The existing authenticated, synthetic-only LangGraph endpoint
`POST /api/v1/cases/{case_id}/preparation/guide` now uses the same approved
official-source RAG implementation as
`POST /api/v1/cases/{case_id}/assistant/ask` for evidence questions.

This change does **not** implement unrestricted legal-advice generation.
The existing RAG pipeline verifies that every generated line is a verbatim
quote bound to a hash-checked, latest human-approved official passage.
No personalized eligibility, fees, mandatory attachments, deadlines,
or government submission state may be inferred from the model.

- The guide's evidence node delegates to `ask_case_question` for
  authenticated, owner-scoped retrieval and verified quotation generation.
- Only its `answer_generated` status authorizes displaying the returned
  `answer`; otherwise the guide provides an explicit evidence-abstention
  message while showing any available approved excerpts.
- Evidence references retain exact citation ID, official title, URL, excerpt,
  and source-verification semantics of the existing assistant endpoint.
- English and Italian user-facing framing is deterministic; source quotations
  remain **original-language Italian**, not unverified translations.
- The case UI displays a verified quotation, alongside official-source links.
  In the optional encrypted Preview conversation feature from PR #53, verified
  quotes are saved as **historical** conversation text, not live evidence.
- Non-evidence graph actions (intake, next step, case status, document review)
  still use current confirmed facts, rule evaluation, and read-only tools.

## Model usage and limitations

- The configured model is only consulted when an approved relevant source is
  available to the RAG generator. For unambiguous official-source requests,
  deterministic tool routing avoids a second model-selection call.
- For ambiguous requests, optional model selection may consume one model call
  in addition to any RAG generation. Both use the existing per-user quota.
- Without `ENABLE_ASSISTANT_API`, the existing read-only fixed-source guide
  remains available and no AI answer is generated.
- English natural-language queries may currently abstain against Italian
  lexical-only evidence when multilingual embeddings are not available.
  This is a known retrieval-quality limitation, **not** proof that an
  administrative rule does not apply.
- The current RAG verifier checks quote provenance and exactness, not
  relevance, completeness, current administrative applicability, or an
  explanation in the user's language. A later retrieval-language improvement
  must preserve the existing evidence gates and tests.

## Safety, deployment, and test evidence

- No municipality/source/rule approval, user-confirmed fact, document review,
  or government submission can be changed by the RAG model.
- No live Auth0 users, documents, model credentials, or external model provider
  are used by the synthetic tests.
- This PR builds on the unmerged encrypted-conversation-history PR #53 and
  deliberately makes **no** Vercel or Neon deployment request.
- Backend offline regression tests exercise approved quotations, unauthenticated
  and cross-owner access, source revocation, missing evidence, missing model,
  generated invented claims, provider failure, and historical encrypted storage.
- Full GitHub Backend and Frontend CI validate Python, PostgreSQL migrations,
  TypeScript, Next.js build and smoke tests. Tests do **not** establish real
  model-provider latency, answer quality or success in a live browser.
- Real-model synthetic evaluation is still needed before claiming full MVP
  agent completion. Production remains unchanged.
