# Unified saved-case journey (thesis MVP)

## Behavior

The signed-in user sees **one case journey** at the top of the saved-case
workspace. It connects seven existing stages: initial scope questions,
confirmed categorical intake, optional AI explanation, approved-source
checklist, private-document review (only when enabled), draft PDF package,
and official user-only ANPR handoff.

The next recommended product action is calculated server-side from the
**actual saved case** and **currently approved source evidence**, never
from an LLM or a browser-supplied administrative decision.

This release does not enable real files, turn on assistant privileges,
automatically submit to authorities, or claim legal eligibility. The
existing AI panel remains informational and, if enabled, provides prose
only. The signed rules always control the source-backed checklist.

## APIs and persistence

- `GET /api/v1/cases/{case_id}/workflow`: Auth0 owner-scoped journey with
  current progress, reviewable signed actions, document-review status,
  package readiness and an explicit next action. Returns no full case ID,
  raw document text or private-document ID.
- `PATCH /api/v1/cases/{case_id}/workflow/checklist`: Strict payload:
  `{"item_id":"reviewed_signed_action","reviewed":true|false,
  "fingerprint":"<64-char-digest>"}`. Requires current owner, supported
  confirmed intake, exact signed action, and fresh fingerprint. The
  original case row is locked before the intake row.
- Frontend Next.js routes proxy through server-side Auth0; mutations require
  same-origin requests and a small exact JSON schema. No API tokens appear
  in the browser.
- Migration `20261109_0016` adds `case_intakes.checklist_progress` (JSON)
  and `progress_fingerprint` (nullable SHA-256 hex). It does **not**
  store official approval or document verification statuses.
- The fingerprint binds canonical confirmed facts, scope answers, current
  ruleset, signed action text, exact citation/version/original URL,
  review/retrieval timestamps. Edits to intake facts reset progress;
  scope changes erase intake and progress; a changed or revoked source
  disables old marks and returns a fresh set only after renewed approval.
- Review marks are user-only **read acknowledgment**. They do not modify
  signed checklist `needs_user` status, the PDF package's approval claims,
  or any official submission. A reviewed action is not proof that the user
  executed it.

## Integrated website

The prior parallel checklist and package panels are replaced by one
case-journey panel. It shows stage status and navigation, one safe next
action, citation-linked signed actions with persistent review checkboxes,
document-review link when available, explicit outstanding package
warnings, an authenticated draft PDF download and official ANPR handoff
anchor. Intake save/correction/deletion and scope edits cause a refresh.
The earlier approved-source registry and optional case-aware AI remain
accessible within the same saved-case workspace.

## Validation

GitHub Actions backend tests cover anonymous/cross-account access,
partial scope, intake confirmation, review mutation, stale fingerprint,
citation revocation, audit reapproval, changed intake facts, scope
invalidation, and preservation of `official_submission=false`.
Frontend tests reject forged rule IDs, links, fake approvals, and
client-injected facts. Run PostgreSQL migration smoke tests, TypeScript,
and Next.js build.

**No Vercel calls, builds or deployments are permitted for this task.**
Production Neon revision `0016` should only be applied after CI passes,
after clone preflight, and with recoverability checked.

This is a synthetic-only thesis MVP vertical slice. Real documents need
separately verified privacy/scanner/retention operations and authenticated
two-account browser E2E. Live deployment is separate from GitHub merge.
