# PracticaMIA release blockers verified 5 November 2026

This report separates shipped code, staging schema, third-party deployment
constraints and official legal-source approvals. Do not claim the product is
a working legal advisory agent while any blockers below remain.

## Verified code and tests

- GitHub main contains PR #22: exact-quote source verification and a
  pseudonymous database-backed per-user daily LLM call budget. A quoted
  statement is visible only when its entire content is present in the
  associated exact approved passage. The strict gate **does not** establish
  suitability, currency or semantic relevance of that passage.
- PR #21 added real localhost HTTP checks of production/preview guards.
- GitHub Actions PR #22: 129 general backend tests passed, six intentionally
  postponed PostgreSQL tests subsequently passed, 17 frontend unit tests,
  two HTTP smoke tests, TypeScript and Next build passed. All on synthetic
  data and no live LLM provider.
- GitHub main CI passed after the PR merge.

## Database

- Neon production branch: Alembic `20261104_0002` (no knowledge tables).
- Neon isolated staging branch:
  `staging-knowledge-0003-0006-2026-11-05` (name unchanged), Alembic
  `20261105_0008`, with HNSW pgvector and shared daily assistant quota
  table. The branch was migrated only after PR #22 CI passed.
- Staging evidence: 17 official URL candidates, one historical non-EU
  Allegato A PDF original, three exact passages, zero approved versions,
  zero persisted embeddings. Historical PDF remains `pending_review`.
- Source bytes, normalized text offsets and hashes validated. Provenance
  integrity is **not** a determination of contemporary legal applicability.

## Official source access

The project registry has 17 official Milan source references. A direct
re-acquisition attempt from this execution environment cannot establish
original HTTP response bytes (DNS unavailable); earlier exact municipality
requests were HTTP 403 in supported browsing. Do not import search snippets,
reconstructed pages, screenshots or an assistant-generated transcription as
original HTML. Do not bypass official access restrictions.

Recent primary source leads for human checking:
- [Comune di Milano — Cambio di residenza](https://www.comune.milano.it/servizi/anagrafe/cambio-di-residenza) — official page indicates last updated 16 June 2026.
- [Comune support — Come chiedere/cambiare residenza](https://servizicrm.comune.milano.it/centro-supporto/KA-00330/Richiestacambio-residenza-come-procedere) — last updated 23 July 2026.
- [Comune support — Stato della pratica](https://servizicrm.comune.milano.it/centro-supporto/KA-00325/Verifica-stato-pratica-di-residenza) — last updated 13 August 2026.

**Operator action required:** Obtain genuine originals or authorised page
captures from the official host, import through the controlled
`backend/app/knowledge/ingest_source.py` importer as `pending_review`,
compare effective and update dates and cited requirements with current
municipal guidance, then approve each precise version using the reviewer
allowlist workflow. Never approve a 2013 PDF solely to get a chatbot answer.

## Deployment constraint

At last verification both Vercel Production aliases were READY but
reported commit `39566f2`, not the newer GitHub main revision.
A new frontend deployment failed with Vercel HTTP 402
`api-deployments-free-per-day` after exceeding the daily deploy quota.
A backend staging build on `9d73f5a` was READY. Do not present a GitHub
merge as proof the latest build is public, and do not promote a preview as
production to sidestep a quota.

**Operator action required:** Wait for quota renewal or adjust the plan in
Vercel settings, then deploy the exact reviewed main commit to both projects
and inspect READY aliases plus `/health` and frontend routes. No billing
settings or external account upgrades were made automatically.

## End-to-end integration constraints

- The current preview is not enabled or connected to a live model.
- Auth0 real sign-in/callback through the preview and ownership round-trip
  have not been verified with an actual browser session.
- A model requires user-selected provider, privacy review, billing,
  explicit `ASSISTANT_CHAT_MODEL` and securely stored `OPENAI_API_KEY`.
- The assistant HMAC budget requires a secret dedicated to the preview
  (`ASSISTANT_USAGE_HASH_KEY`, min 32 characters) and migrated staging DB.
- An authenticated preview with a genuine current reviewed evidence base
  and controlled model calls must be tested prior to production release.
- Case-specific Italian administrative rules are not implemented.
  The demo scope classification is **not** a government eligibility decision.
- Human reviewer approval and source freshness policy remain release gates.

The correct status is: **tested development foundation; not yet a live AI agent**.
