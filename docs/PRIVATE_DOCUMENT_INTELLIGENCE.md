# Private document intelligence — controlled MVP milestone

## Scope and user-visible behavior

This change extends the **currently disabled** opt-in private-document vault.
It does not activate real-document collection. The existing scanner contract,
user privacy acknowledgement, account ownership checks, encryption keys,
seven-day access expiry, scheduled purge and deletion remain prerequisites.

For a private **housing document only**, after the file has been successfully
uploaded and scanned, the owner can explicitly request local PDF extraction
or, if Tesseract is installed, local image OCR. An allowlisted parser searches
only for clearly labeled:

- Housing basis: registered private rental / owner / guest / other.
- Move-in date: ISO YYYY-MM-DD.

Raw page text is processed in memory and discarded. No identity numbers,
names, rental addresses, arbitrary free text or original document bytes are
returned by the intelligence API or sent to OpenRouter/other LLMs.

Each suggestion has source-page provenance and an evidence-bound candidate
hash. Suggestions are **not** facts. The user selects the supporting evidence,
corrects the proposed typed value if needed, and expressly confirms. The
confirmed review is encrypted using the vault's separate AES-GCM key and
identity-bound AAD, with an independent review domain separator. It remains
a user review, not official authenticity verification.

A read-only comparison checks the **current** owner-confirmed categorical
case intake. It reports match, mismatch, or missing confirmed intake fields.
Corrections do **not** silently overwrite the case intake; changing or
deleting intake invalidates the comparison on the next read. Conflicting
labels inside one document require manual review. Unknown, ambiguous,
unsupported and unreadable documents never silently pass.

## Routes

- `GET /api/v1/cases/{case_id}/private-documents/{document_id}/intelligence`
- `POST .../intelligence/extract` — idempotent after first extraction.
- `PUT .../intelligence/review` — requires exactly mapped candidate IDs,
  bounded typed corrections, unchanged extraction digest and explicit `confirm`.
- Corresponding explicit Next.js Auth0-proxy routes reject cross-origin
  writes and unsupported JSON.

No route downloads plaintext, submits to ANPR, evaluates eligibility or
declares any document legally valid. Authenticated owners receive a 404
for another account's file.

## Data lifecycle

Migration `20261109_0015` adds a nullable encrypted
`private_case_documents.review_ciphertext` field. There is no new
long-lived table. The review disappears with the original private document
on owner deletion, case deletion or seven-day purge. Backups/PITR may outlive
active storage per the provider's own retention period.

## Verification and activation gates

1. GitHub Actions backend + frontend suites pass (including TypeScript/build).
2. Apply additive migration on a disposable Neon clone. Check existing cases,
   reviewed sources and vault rows; use recovery branch before production.
3. Merge PR without triggering **any manual Vercel calls, builds or deploys**.
   A GitHub merge alone is not proof of a live website update.
4. Before **any real upload or parsing**, independently review the full data
   controller privacy notice and lawful basis, DPA/subprocessors, scanner
   service, log redaction, encryption-key management, abuse limits,
   deletion monitoring, OCR availability, international data transfers and
   actual backup retention. Operator approval flags alone do not substitute
   for this review.
5. Run full authenticated two-user browser E2E with **fictional** housing PDFs,
   identity-document extraction denial, malformed/unsafe PDFs, scanner outages,
   stale candidate rejection, cross-account access, expired-file deletion,
   misaligned move dates, ambiguous labels and source-review fail-closed behavior.
6. Release only through approved deployment. The existing Vercel-hosted
   production site is not updated by this task unless the host deploys it.

The next milestone remains preparing an **exportable, user-reviewed package**,
with official handoff instructions and no simulated government approval.


## Review corrections and document-type boundaries

A saved, user-confirmed housing review can be reopened and corrected while
its encrypted record and extraction fingerprint remain valid. The UI restores
the previously chosen evidence and corrected typed values; the backend still
requires an explicit confirmation for every field. Italian dates explicitly
labeled as a move/transfer date may be normalized from `DD/MM/YYYY` or
`DD.MM.YYYY` to canonical `YYYY-MM-DD`; an unlabelled rental commencement
date is never inferred to be the applicant's move date.

A confirmed document value without a matching confirmed case fact is reported
as `needs_case_information`. It blocks draft export rather than being silently
treated as an equivalent match. Identity and miscellaneous supporting documents
may be stored only when the opt-in vault is enabled; they have no approved
automated extractor. They remain explicitly **unverified warnings** in the
non-official draft, not impossible-to-complete automated review blockers.

The route remains limited to supported, reviewed Milan cases. There is no
claim that a document is legally valid, that uploaded files satisfy all
mandatory attachments, or that a government application has been submitted.
