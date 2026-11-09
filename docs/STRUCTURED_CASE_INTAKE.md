# Structured, persistent case intake — first Milan workflow

## Purpose and approved boundaries

After the five initial product-scope answers, collect a second, explicitly
confirmed set of facts supporting the **reviewed first-route decision
conditions**. The canonical facts are stored in a dedicated, case-owner-scoped
database row; they are not inferred from chat messages or document OCR.

This milestone is the next stage of the MVP, **not a full real-person intake**.
Until the identity-document privacy release is approved, the UI explicitly
asks for **fictional example data**. Names, street addresses, tax IDs,
passport numbers, free-text notes, document bytes and arbitrary JSON fields
are never accepted by these endpoints. The move-in date is optional and does
not trigger any legal deadline calculation.

## Recorded facts

- `citizenship_class`: Italian / non-Italian / unknown
- `registration_context`: previously registered in Italy / arriving from
  abroad / unknown
- `destination_municipality`: Milano / other / unknown
- `household_scope`: individual / joining a household / multiple applicants
  / unknown
- `housing_basis`: registered private rental / owner / guest / other / unknown
- `move_in_date`: optional, ISO calendar date

These categories correspond to the five typed condition keys in the reviewed
first-scenario ruleset. **They do not imply that the scope questions establish
citizenship or that every rental agreement is registered.**

## API and UX

- `GET /api/v1/cases/{id}/intake`: owner-scoped saved facts and provenance
- `PUT /api/v1/cases/{id}/intake`: strict full replacement of the limited
  fact map. Drafts may omit fields. Confirmation requires all five categorical
  fields present and not unknown.
- `DELETE /api/v1/cases/{id}/intake`: remove saved intake.
- The Next.js BFF authenticates requests server-to-server, verifies same-origin
  writes and bounds request bodies. The browser receives no API token.
- Saved values are tagged as `user_entered`, with either `draft` or
  `user_confirmed` verification state.
- Scope edits **delete** downstream intake, preventing stale confirmations.
- Case deletion also deletes the corresponding intake row.
- Review, correction, save, resume, and erase are available in English and
  Italian in the saved-case workspace.
- Candidate mismatch is a product first-scenario limit, **never** a
  government eligibility decision.
- No new prompts, LLM requests, official submissions, attachment requirements,
  or authorization to upload identity documents are introduced.

## Operational sequencing

1. GitHub Actions CI must pass backend PostgreSQL migration tests, frontend
   unit tests, types, and Next.js build. **No direct Vercel calls or builds.**
2. Apply additive Alembic `20261109_0014` on a disposable Neon clone.
   Preserve existing cases, approved sources and document-vault schema.
3. Create a recovery branch and apply the migration to production through
   Neon's native SQL interface; do not copy staging data.
4. Merge GitHub PR after all available CI checks pass.
5. **Deployment remains separate.** The existing production URL is hosted
   by Vercel; pushing code to GitHub does not establish a successful
   deployment. With Vercel use prohibited by the operator, do not claim
   that the new code is live unless independently verified.
6. Real-life address fields and documents should be added only with
   appropriate privacy, secure storage and deletion controls; detailed
   rules/checklist wiring is the subsequent milestone.

## Acceptance tests

A signed-in owner can save a partial draft, sign out and back in, and resume.
An owner can explicitly confirm all five required categories; missing and
invalid values fail. Changing scope or deleting the case invalidates
and erases facts. An unrelated account receives 404. No identity, address,
free-text or unexpected field is accepted. Review status never claims an
administrative determination.
