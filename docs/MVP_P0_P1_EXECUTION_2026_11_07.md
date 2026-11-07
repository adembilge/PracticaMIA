# 7 November 2026 — MVP milestones 1 and 2

## Milestone 1 — Authenticated preparation Preview

**Implemented infrastructure:** The isolated Neon branch `preview-preparation-mvp-20261107` (not production) was advanced from Alembic `20261106_0010` to `20261106_0011`. The change was an additive transactional application of the exact DDL in `backend/migrations/versions/20261106_0011_preparation_preview.py`, creating `case_preparations` and `case_documents` and their three indexes. SQL read-back verified both tables and revision `0011`.

**Isolation verified:** Production remains at `20261104_0002`; the separate knowledge staging branch remains at `20261106_0010`. Neither contains the preparation tables.

**Preview activation procedure:** Existing Auth0 Preview credentials are scoped to the Vercel branch `preview/auth-review-isolated`; never replace these with Production credentials. The paired branch requires:

- Backend Preview: an isolated branch-only `DATABASE_URL` pointing to the **preparation** Neon branch; its matching SHA-256 `PREPARATION_DATABASE_FINGERPRINT`; `PREPARATION_DOCUMENT_KEY` holding a unique 32-byte randomly generated base64 key; `PREPARATION_TARGET=isolated_staging`; `ENABLE_DEMO_CASE_API=1`; `ENABLE_KNOWLEDGE_CATALOG_API=1`; `ENABLE_PREPARATION_API=1`.
- Frontend Preview: existing Preview-only Auth0 identity and callback configuration, exact backend Preview origin and `ENABLE_PREPARATION_UI=1`. Pair the frontend and API on the same reviewed commit. Keep the independent source-review UI available to its existing allowlisted reviewer only.
- Use the preview-only `/cases/{caseId}/preparation` route after creating a synthetic authenticated case. **No real personal information or documents.** Run the existing opt-in two-account authenticated browser harness in `.github/workflows/authenticated-preview-e2e.yml`; a green offline CI result is not a live browser pass.

**Acceptance:** Synthetic authenticated sign-in, case create/save/resume, tiny PDF upload, extraction, candidate confirmation, document review, checklist blocked pending actual rules, owner isolation, disabled production route. Do not mark live E2E complete without actual browser output and matched Preview deployment URLs.

## Milestone 2 — First supported procedure, approval draft

**Selected candidate:** Italian citizen already registered as resident in Italy, moving individually to Milano, not aggregating with an existing household. This is a product boundary for a small first workflow, **not** a final legal determination.

**New source-linked proposal:** `requirements/milan-residence-change/italian_individual_candidate_v1.json` references three exact passage IDs from the existing human-approved municipal source `milano-italian-residence-change`:

| Topic | Approved passage ID | Meaning evidenced |
| --- | --- | --- |
| Residence-change route and timing | `e139e910-3a89-4994-b450-b5107d8db7dd:0000` | Municipality says notify Anagrafe within 20 days using ANPR |
| Aggregation exception | `e139e910-3a89-4994-b450-b5107d8db7dd:0003` | Joining an existing household entails additional consent |
| TARI follow-up | `e139e910-3a89-4994-b450-b5107d8db7dd:0005` | Separate declaration of housing situation for TARI |

Source URL: https://servizicrm.comune.milano.it/centro-supporto/KA-00371/ (dated 23 July 2026, checked 7 November 2026).

The approved passages do **not** establish a complete list of required ANPR attachments or form fields. The separate municipality landing page, general FAQ and Allegato 1 currently have no approved registry versions. The draft deliberately invents no mandatory document category and therefore **must not be promoted to an active ruleset or offered as a complete filing package**.

**Human approval required to finish:** A designated reviewer must independently review the applicable scope and complete requirements, resolve missing attachments and handoff, record a signed and complete catalog, then rerun all golden route/negative/revocation tests. Do not change the production catalog `backend/app/rules/catalog.json` or fabricate an Ed25519 review signature.

## Test coverage added

`backend/tests/test_milan_rules_candidate.py` exercises:
- Candidate and real catalog remain pending; no signature.
- Exact source passage IDs and no fictional evidence references.
- Deny-by-default candidate decision and no package.
- Hypothetical in-memory route-only fixture for technical evaluation.
- Missing values for each routing fact (4 cases).
- Wrong citizenship, foreign arrival, other municipality, joining household and multi-person scenarios (5 cases).
- Independent source revocation (3 cases).
- No invented attachment obligation, separate TARI action, metadata flip not granting approval, rejected evidence producing a blocked workflow.

All hypothetical activation is only inside tests. A green CI is not administrative approval.
