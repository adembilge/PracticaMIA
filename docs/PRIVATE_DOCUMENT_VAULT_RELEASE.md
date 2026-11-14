# Private document vault — production release checklist

## Scope
New **separate** `private_case_documents` table and API. The synthetic-only
`/preparation` APIs, LLM prompts, and existing `case_documents` are NOT exposed
or relaxed. The private vault is disabled by default. Database migration and
merge **do not** activate private uploads.

## Implemented safeguards
- Auth0 access token verification in the backend; user case ownership is
  rechecked for listing, upload and deletion. Next.js only forwards tokens
  server-to-server, checks Origin, sanitizes multipart form data, and does
  not return document bytes.
- Mandatory explicit acknowledgement of notice
  `private-documents-2026-11-v1` and a named controller/contact, with a
  distinct server-side release approval flag. This acknowledgement is **not**
  a claim that GDPR consent is the correct Article 6 lawful basis.
- 2 MiB PDF/PNG/JPEG allowlist; MIME magic checks, strict PDF parse
  (1–15 unencrypted pages), bounded image dimensions, no active PDFs.
- **Fail-closed external malware scan**: HTTPS POST of file bytes only,
  without user identity/case/filename, authenticated with a service credential.
  Scanner responds 200 JSON with exact `{"status":"clean","sha256":"<hex>"}`.
  Malware, mismatch, errors, timeout and redirects reject the upload.
  The scanner vendor, processing location, DPA, and subprocessor disclosure
  must be reviewed before activation.
- Random nonce and 256-bit AES-GCM per document, separate production key
  from Preview preparation; AAD binds case, owner and document identity.
  No original file download or AI/LLM forwarding route exists.
- No more than five active documents per case; upload writes serialized using
  a PostgreSQL case-row lock.
- Database expiration seven days from upload. Expired files are hidden.
  Users can delete immediately from active storage. Scheduled daily purge
  removes expired encrypted bytes, in bounded batches, and case deletion
  cascades to private documents. Physical purge may occur after the access
  expiry and backup/PITR copies can outlive active storage.
- Private data routes return `Cache-Control: private, no-store`.
- No official submission or eligibility inference is performed.

## Prerequisites BEFORE enabling real users
1. Execute additive Alembic migration `20261109_0013` on an isolated
   production clone and test preservation of cases; then snapshot and
   apply to production. Never copy Preview applicants or test document bytes.
2. Obtain **independent operator/legal privacy review**: verify controller
   identity, lawful basis, processor/subprocessor contracts and DPA,
   data residency/transfers, backup erasure windows, access/deletion rights,
   breach procedure and published full privacy terms. Replace draft
   `/privacy/documents` text as needed. Do **not** merely flip the flag.
3. Deploy a private trusted malware-scan endpoint implementing the exact
   checksum-echo contract above; monitor failures and verify test malware
   rejection (for example, an approved harmless antivirus test fixture).
4. Generate a **new dedicated 32-byte base64 AES key**, a random 32+ character
   scanner API credential and a **random 32+ character CRON_SECRET**.
   Store them as Sensitive in backend Vercel Production; never in GitHub,
   chat, browser or public Preview variables.
5. Configure backend Production variables:
   `ENABLE_PRIVATE_DOCUMENT_API=1`,
   `PRIVATE_DOCUMENT_KEY`,
   `PRIVATE_DOCUMENT_SCAN_URL`,
   `PRIVATE_DOCUMENT_SCAN_HOST`,
   `PRIVATE_DOCUMENT_SCAN_TOKEN`,
   `PRIVATE_DOCUMENT_PRIVACY_APPROVED=1`,
   `PRIVATE_DOCUMENT_CONTROLLER`,
   `PRIVATE_DOCUMENT_CONTACT`, and `CRON_SECRET`.
   Startup refuses incomplete config or a schema other than 0013.
6. Configure matching non-secret frontend Production values:
   `ENABLE_PRIVATE_DOCUMENT_UI=1`,
   `PRIVATE_DOCUMENT_PRIVACY_APPROVED=1`,
   `PRIVATE_DOCUMENT_CONTROLLER`,
   `PRIVATE_DOCUMENT_CONTACT`.
   Frontend and backend must agree on the notice version.
7. Inspect Vercel Cron (daily 03:00 UTC), monitor consecutive non-2xx and
   `more_expired`, and run a manual authorized purge test in a disposable
   database. Daily cleanup does not guarantee instantaneous removal exactly
   at the expiry moment. Make operator backup-retention disclosure accurate.
8. Run **two-account Auth0 live browser tests** with synthetic documents:
   user A cannot read/delete B's documents, malformed files and malicious
   scanner verdicts fail, deletion and expiry work, no LLM/file leakage,
   no official submission, and recovery behavior is documented.
9. Release to a limited beta only when the privacy notice, vendor controls,
   operational monitoring, and browser E2E are all verified. Maintain the
   public fictional walkthrough independently.

## Operational limitations
- No persistent per-user scanner-cost rate limiter yet; the five-document
  per-case cap is not a global upload-frequency quota. Configure edge
  throttling and a durable owner quota before wider rollout.
- A Vercel Cron invocation may fail or be delayed; alerting/monitoring is
  necessary to make any retention commitment meaningful.
- Neon snapshots, PITR and third-party backups have separate retention periods.
  Immediate deletion removes the active database row, **not all backups**.
- This code does not independently determine GDPR compliance, provide legal
  advice, or replace a data-protection impact assessment when necessary.
- The operator still needs to choose and disclose a lawful basis; a checkbox
  is an acknowledgement and is not automatically valid GDPR consent.
