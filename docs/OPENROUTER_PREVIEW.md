# OpenRouter free-model support (isolated Preview only)

The assistant can use **OpenRouter**, an OpenAI-compatible endpoint, in place of
the OpenAI API. This does not enable or change Production. Do not send real
identity documents, addresses, case details, or municipal administrative advice
to free-model providers.

## Provider configuration

Set the following **only** on the trusted Preview branch in Vercel
`practicamia-api`:

| Variable | Value |
| --- | --- |
| `ASSISTANT_LLM_PROVIDER` | `openrouter` |
| `ASSISTANT_CHAT_MODEL` | `openrouter/free` |
| `OPENROUTER_API_KEY` | Stored securely as sensitive; never commit |
| `ENABLE_ASSISTANT_API` | `1`, only after prerequisites below |
| `ASSISTANT_USAGE_HASH_KEY` | Unique randomly generated secret, at least 32 characters |
| `ASSISTANT_DAILY_LIMIT` | `10` (optional default) |

The model factory uses `https://openrouter.ai/api/v1`, and rejects any
OpenRouter model other than `openrouter/free` or a slug ending in `:free`.
The original `OPENAI_API_KEY` integration is preserved when
`ASSISTANT_LLM_PROVIDER=openai` (or the variable is omitted).

The Preview frontend also needs `ENABLE_ASSISTANT_UI=1` on the same trusted
branch. All prior Auth0, case API, knowledge catalog, knowledge search, and
isolated staging database prerequisites remain mandatory. The existing
assistant API refuses to start in `VERCEL_ENV=production` even if a flag is
accidentally set there.

## Verification

1. Run `pytest -q backend/tests/test_openrouter_provider.py` with the
   project's configured Python dependencies (or from `backend`, run
   `pytest -q tests/test_openrouter_provider.py`).
2. Deploy both Preview projects for the trusted branch; verify `/health`.
3. Sign in to an *owned synthetic case* and open `/cases/{id}/assistant`.
4. Ask a question against an **already approved and current** synthetic/
   reviewed evidence passage. `answer_generated` proves the LLM returned a
   strictly quote-verified answer. `insufficient_evidence` proves the evidence
   safety gate withheld the model call. `model_not_configured` indicates
   provider settings were not picked up, while `generation_unavailable` or
   `unverified_answer` requires separate diagnosis.
5. Check OpenRouter account activity and quota for an observed real request.

No public or production AI guidance is authorized by these changes.
OpenRouter's `openrouter/free` selects a model dynamically, so output quality
and support may vary. Free inference is rate-limited and can be interrupted.
Provider privacy terms differ; do not use personal data for this initial setup.

If a key was shared in chat, revoke/rotate it after testing and update the
Preview-only sensitive Vercel environment variable.
