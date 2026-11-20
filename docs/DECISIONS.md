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

## D-004 — Align the scope questions with the signed Milan route (14 November 2026)

The product owner approved aligning the entry flow with the existing signed route. The first question asks about prior registration anywhere in Italy. The second asks whether the destination is in Comune di Milano. Moves within Milan and moves into Milan from another Italian municipality follow the same route if the separately confirmed intake matches the signed conditions. A saved `Yes` to the former narrower registration question remains valid. A saved `No` remains blocked until the user answers the updated question. See [the reviewed checklist boundary](REVIEWED_CASE_CHECKLIST.md#exact-release-boundary).

## D-005 — Reconcile the legacy roadmap without certifying completion (17 November 2026)

The product owner authorized work to resolve the roadmap blockers. The [criterion-by-criterion reconciliation](ROADMAP_RECONCILIATION.md) reviewed all 94 parent tasks and 12 required RAG subtasks against checked-in and dated evidence. The administrative `unreconciled` marks can be replaced by `partial` or `blocked`, and the global reconciliation hold can be cleared. This decision does not approve the product vision, official sources, rules, privacy controls, beta, deployment or any task completion. Individual dependencies and human gates remain in force.

## D-006 — Merge eligible PracticaMIA pull requests without another prompt (18 November 2026)

The product owner authorized automatic merges going forward. Review the actual diff and relevant checks, confirm the pull request head, and merge within the repository's required checks and approvals. Keep release and source approval decisions on their existing review paths.

## D-007 — Use one chatbot for the Italian bureaucracy experience (20 November 2026)

The product owner wants all Italian administrative questions to start in the same chatbot. The first interaction is a free-text message. Clarifications, case facts, reviewed answers, sources, next actions and resumption belong in that same interface. Establish the relevant procedure and jurisdiction from the conversation. Let the user confirm a case or a proposed change in the chat when one is needed.

Use this approach for all three Phase 4 pilot scenarios. A vetted official handoff appears in the conversation at the applicable step. Existing release and claim review requirements still apply.

## Decisions still unresolved

- Currency and applicability reviews for the approved first Milan scenario, especially the officially required attachments and exceptions.
- Live reviewer authorization, refresh/resumption, and private-document isolation beyond the completed manual Auth0 case checks. See [acceptance evidence](ACCEPTANCE_TESTING.md).
- Full conversational-agent and retrieval quality benchmarks, provider routing and privacy of model inputs.
- Operational authorization to enable private documents, scanner, encryption/retention lifecycle and live personal-data handling.
- Backup and restore exercise, observability coverage, private user validation, and explicit production release sign-off.

Historical decisions above are dated records. Later code, database changes, and approved-source events must be reconciled using current evidence; they do not retroactively alter the human decisions recorded at the time.
