# First-route case preparation draft and PDF export

## Scope
A user who has completed the five original scope answers and explicitly
confirmed the separate categorical intake can request an **owner-scoped,
source-reviewed, downloadable preparation draft**. The signed first Milan
rules are re-evaluated with current approved source snapshots and citations
on EVERY request. PDF bytes are created on demand and NEVER persisted.

The export contains:
- Case reference prefix and generation timestamp.
- Six or fewer explicitly user-confirmed categorical residence facts, including
  an optional move date; no personal addresses, names or document numbers.
- Five exact signed English action descriptions and per-item links/citation
  IDs/review dates to the originally approved official source versions.
  The historical ANPR guide is visibly marked archived.
- Counts, limited review status and comparison outcomes for encrypted private
  documents, when the opt-in private vault is operational.
- Outstanding issues and missing document-review signals.
- Official ANPR and Milan service links, with an explicit instruction that
  the user alone may submit using the current official portal.

**This is NOT a government application, approval, completed official attachment
checklist, or submission receipt.** Neither the user nor the AI can mark
`official_submission` true. No government APIs are called.

## Download gates and behavior
- Incomplete original scope, unconfirmed intake, unsupported first-route facts,
  revoked/replaced citation, invalid signed rules, or unsupported procedure:
  no actions and HTTP 409 for the PDF export.
- A supported, confirmed case with no uploaded private documents may download
  a clearly marked **reviewable draft** with `no_documents_reviewed` or
  `private_document_processing_not_enabled` warnings. It is NEVER labeled
  `submission_ready`.
- Existing private documents with incomplete extraction, unsupported category,
  ambiguous labels, unreadability, mismatch against current intake, missing
  confirmed facts, unscanned status or corrupted encrypted metadata block the
  PDF export. The JSON preview still explains what needs resolution, except
  that corrupted encryption fails closed with HTTP 503.
- Document data is used only when the existing default-off privacy/scanner
  vault gate is explicitly enabled. PDF never contains original document
  bytes, OCR page text, filenames, full case IDs, file IDs or identity data.
- User-controlled "reviewed" never means that a document is authentic or
  legally sufficient.
- No new database table or migration is required (current Neon revision
  `20261109_0015` is sufficient). Only `reportlab` moves from optional
  dev dependencies to production Python dependencies.

## Routes
- `GET /api/v1/cases/{id}/package` -> private no-store manifest.
- `GET /api/v1/cases/{id}/package/pdf` -> private no-store PDF attachment
  only after live owner/requirements/review checks.
- Both routes authenticate and check ownership in the backend; the Next.js
  BFF obtains Auth0 credentials on the server and relays bytes with strict
  PDF magic, Content-Type and size validation. Browser tokens are never
  exposed.
- New saved-case intake UI shows package preview, blockers, source/action
  count and a download link that activates only for an allowed draft.

## Verification and release
- GitHub Actions backend pytest (with real PDF text extraction and negative
  auth/scenario/source/document tests); frontend node tests; TypeScript and
  Next.js build. Run E2E separately before beta.
- No Vercel calls, sandboxes or deployments. A GitHub merge does not make
  the package appear on the Vercel-hosted website until a permitted deployment
  succeeds.
- User's security release gate for real private documents stays unchanged:
  controller/privacy notice, contracts, malware scanner, key management,
  retention monitoring and two-account end-to-end validation.
- No external forms have been adopted or officially certified. Official
  application form prefill would require a separately reviewed template.

## Following milestone
Connect case navigation, cited checklist, document review and package status
into one coherent journey, with persistent user-only checklist progress,
then perform controlled E2E tests and release acceptance.


## Draft export and unsupported attachments

An identity or miscellaneous supporting document can be uploaded into the
private vault without an automated extractor. Its status is
`unsupported_category`. It is shown as **unreviewed** in the manifest and
draft PDF, and cannot be used as proof of eligibility or attachment
completeness. Such a document does not, by itself, prevent export of a
clearly non-official draft.

Supported housing documents **do** block export until extracted and
explicitly reviewed. A conflict, ambiguity, failed extraction or reviewed
value with no matching confirmed case fact (`needs_case_information`)
continues to block export. The exported PDF contains only bounded categorical
metadata and status labels; it does not embed uploaded document bytes,
full OCR text or personal identifiers.
