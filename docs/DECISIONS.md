# PracticaMIA — development decision log

Log actual user-approved decisions separately from proposals and inherited system constraints. Generated content is not evidence of a source review, legal determination, or owner sign-off.

## D-001 — Preserve source roadmap without renumbering (6 November 2026)

**State:** tracking implementation under review.  
**Source:** `PracticaMIA_Complete_Project_Specification.md`, sections 24 and 25.

The canonical project roadmap has 12 stages and 94 parent tasks. Task 45 and Task 50 have six subtasks each. The tracker follows the default sequential order in the specification; Task 55 retains its explicit example dependencies [47, 53, 54]. Changes to dependency ordering require a documented reason and review.

## D-002 — Do not backfill success from code existence (6 November 2026)

**State:** governance safeguard under review.

Existing code and merged PRs predate a tracked task-state system. Every generated task therefore has `status: pending`, `evidence_review: unreconciled`. This is an *administrative placeholder*, not a claim that implementation is absent. Do not remove the top-level execution blocker until existing work has been assessed against each acceptance criterion with a reference to actual evidence.

## D-003 — Isolate real authenticated tests (6 November 2026)

**State:** security baseline inherited from the independent audit and draft PR #32.

Real two-account Auth0 tests require two dedicated synthetic accounts, a separate allowed Preview callback origin, a paired isolated frontend/backend, and the migration-compatible staging Neon branch. Do not bypass authentication challenges or copy production session secrets to preview. Reviewer-only article access is testable without approving any source.

## Decisions still unresolved

- Currency and applicability reviews for the approved first Milan scenario, especially the officially required attachments and exceptions.
- Real browser Auth0 and two-account session acceptance against the deployed frontend and backend.
- Full conversational-agent and retrieval quality benchmarks, provider routing and privacy of model inputs.
- Operational authorization to enable private documents, scanner, encryption/retention lifecycle and live personal-data handling.
- Backup and restore exercise, observability coverage, private user validation, and explicit production release sign-off.

Historical decisions above are dated records. Later code, database changes, and approved-source events must be reconciled using current evidence; they do not retroactively alter the human decisions recorded at the time.
