# Controlled P0 preparation vertical slice — synthetic preview only

**Status:** implementation under review, NOT a completed Milan MVP. No real administrative source has been approved by this change. The current `backend/app/rules/catalog.json` is explicitly `pending_review` and has zero activated rules. Real-case package preparation must therefore return `blocked`.

## Added capabilities (code)

- **Evidence-gated deterministic rules:** bounded `all/any/not/equals/in/exists` conditions, three-valued evaluation, missing-field detection, explicit route selection, requirements and document checklist. A fully attested, versioned ruleset, reviewer identity, completeness declaration, and verified approval of *every* cited source passage are mandatory. Source revocation immediately invalidates eligibility output.
- **Bounded LangGraph:** read-only `evaluate_approved_rules → validate_confirmed_documents → prepare_reviewable_package` graph. No LLM or shell actions; no government API integration. Source status and facts are refreshed on each API request.
- **Private preparation state:** authenticated owner-bound case facts and AES-GCM-encrypted case/document metadata; separate encrypted original bytes. Exactly scoped preview-only API. Explicit synthetic-data header is an additional use restriction, not proof an uploaded file is fictional.
- **Document processing:** 2 MiB limit, PDF/PNG/JPEG signature checks, a bounded digital-PDF text path using pypdf, optional Pillow/Tesseract OCR for images, provenance-anchored address suggestions, and required explicit field and document review. No field is treated as verified because a parser or model reported it.
- **Conflict detection:** mismatched user-confirmed and document-confirmed fields block package preparation. Missing approved-rule document categories block preparation. Deletion invalidates package review and erases the stored ciphertext and extracted data, including on parent case deletion.
- **User-controlled package:** structured data/checklist/citation appendix, deterministic review digest, explicit user approval, and links resolved from approved official passages. It does not prefill an official PDF or submit documents. A synthetic fixture result cannot be equated with government acceptance.
- **PostgreSQL migration `20261106_0011`:** additive private preparation/document storage. **Not automatically applied.** Production still remains on the older schema and these routes must remain disabled.

## Local configuration

Requires all of the following for a controlled Preview environment:

```env
VERCEL_ENV=preview
ENABLE_DEMO_CASE_API=1
ENABLE_KNOWLEDGE_CATALOG_API=1
ENABLE_PREPARATION_API=1
PREPARATION_DOCUMENT_KEY=<base64 encoding of 32 random bytes, preview-only>
```

Plus the existing Auth0 JWT settings and an isolated PostgreSQL branch explicitly migrated to `20261106_0011`. Do **not** reuse a production key or production case database. The key must be securely stored and retained for encrypted document recovery. Rotating or losing it without an approved re-encryption process makes data unreadable.

The server refuses `ENABLE_PREPARATION_API=1` when `VERCEL_ENV=production` and refuses invalid or missing encryption keys. API examples and integration tests use synthetic facts/documents exclusively.

## New API contracts

Under `/api/v1/cases/{case_id}/preparation`, for the JWT-authenticated case owner:

- `GET /`, `PUT /facts`
- `GET /checklist`
- `POST /documents` (multipart upload with `X-PracticaMIA-Synthetic-Only: YES`), `GET /documents`
- `POST /documents/{document_id}/extract`
- `POST /documents/{document_id}/confirm-fields`
- `POST /documents/{document_id}/review`
- `DELETE /documents/{document_id}`
- `GET /package`, `POST /package/approve`, `GET /handoff`

The original authenticated synthetic-case and unrelated knowledge endpoints remain unchanged when the feature flag is off.

## Tests and remaining P0 gates

`backend/tests/test_preparation_rules.py` tests truth tables, source invalidation, incomplete catalogs, LangGraph branches, conflicts, private encryption and synthetic PDF extraction. `backend/tests/test_preparation_api.py` tests the end-to-end synthetic owner-scoped HTTP flow, cross-user denial, confirmation, package digest, source revocation, deletion and production startup refusal. GitHub CI must run these in addition to existing backend and frontend suites.

**Still required before real MVP:**

1. **Real human approval of currently applicable, versioned municipal material** and complete, independently reviewed scenario-specific rule catalog. Staging currently has 13 source versions but zero approved and zero real embeddings. No agent may self-approve or silently activate these.
2. **Official-form mapping and accepted submission instructions** from verified sources; the generated JSON package is a preparation artifact, not an officially accepted form.
3. **Production-quality document security and UX:** malware scanning, actual private-binary storage/backup and deletion review, retention/consent policy, key rotation, stronger PDF sandboxing, OCR availability and quality evaluation, and full authenticated frontend review journey. Tesseract must be installed separately for image OCR; absent binary yields a controlled unavailable response.
4. **Real Auth0 two-account browser E2E, privacy assessment, bilingual quality, and production/staging migration/release gating.** The new route is deliberately production-disabled.

**Operational safety:** do not use real personal documents against this preview before explicit privacy, access-control and storage review. Do not point new endpoints at production Neon or deploy any migration without authorization. Project governance reconciliation remains open and historical task statuses should not be silently flipped to `completed`.

## Subsequent controls and UI added in this PR

- **Human review signature:** To activate any ruleset, a designated human reviewer must cryptographically sign the canonical catalog. The backend accepts only a valid Ed25519 signature (public verification key in `PREPARATION_RULE_REVIEW_PUBLIC_KEY`), plus a complete scenario-coverage declaration and separately approved current citations. Merely editing `approved_by` does not activate legal requirements.
- **Database identity and schema:** Enabling the API additionally requires `PREPARATION_TARGET=isolated_staging` and, with PostgreSQL, an exact `PREPARATION_DATABASE_FINGERPRINT` SHA-256 checksum of the configured `DATABASE_URL`, and migration `20261106_0011`. A production environment always rejects the preview feature. Generate the fingerprint locally with `python -c 'import os,hashlib;print(hashlib.sha256(os.environ["DATABASE_URL"].encode()).hexdigest())'`. Never print or commit the DB URL.
- **Next.js preview UI:** `ENABLE_PREPARATION_UI=1` exposes a synthetic test-only workspace at `/cases/{id}/preparation` and an authenticated server-side proxy. The UI flag is ineffective when `VERCEL_ENV=production`. Source/pending catalog status is visible, but it cannot be silently converted into a real user checklist or government submission.
- **Verification:** The CI includes a disposable PostgreSQL migration and encrypted-state smoke check plus frontend production-gate and payload validation tests. Green unit tests do not imply human-approved rules, real Auth0 Preview E2E, anti-malware screening, installed Tesseract OCR, or a complete official form.
- **Source research:** [6 November official review candidate dossier](research/P0_OFFICIAL_SOURCE_REVIEW_CANDIDATES_2026_11_06.md). All information in the dossier is **pending human review**, not trusted application guidance.

### Additive backend Preview variables (all off by default)

```env
ENABLE_PREPARATION_API=0
PREPARATION_TARGET=
PREPARATION_DATABASE_FINGERPRINT=
PREPARATION_DOCUMENT_KEY=
PREPARATION_RULE_REVIEW_PUBLIC_KEY=
```

The signed catalog must be generated and reviewed outside the app; keep the Ed25519 private key offline. Neither setting these variables nor passing synthetic CI tests approves municipal law.
