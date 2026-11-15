# Structured, persistent case intake — first Milan workflow

## Purpose and approved boundaries

After the five initial product-scope answers, collect a second, explicitly
confirmed set of facts supporting the **reviewed first-route decision
conditions**. The canonical facts are stored in a dedicated, case-owner-scoped
database row; they are not inferred from chat messages or document OCR.

The saved-case UI asks for **fictional example data**. Names, street addresses, tax IDs,
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
- Changed scope answers clear downstream intake and review marks.
- Case deletion also deletes the corresponding intake row.
- Review, correction, save, resume, and erase are available in English and
  Italian in the saved-case workspace.
- Candidate mismatch is a product first-scenario limit, **never** a
  government eligibility decision.
- No new prompts, LLM requests, official submissions, attachment requirements,
  or authorization to upload identity documents are introduced.

## Persistence and downstream use

Revision `20261109_0014` introduces case intake. Revision `20261109_0016` adds acknowledgement state on the same row. The [checklist](REVIEWED_CASE_CHECKLIST.md), [case workflow](UNIFIED_CASE_WORKFLOW.md) and [draft export](CASE_PREPARATION_EXPORT.md) use confirmed intake. Use the [deployment runbook](VERCEL_NEON_DEPLOYMENT.md) for environment and schema checks.

## Acceptance tests

A signed-in owner can save a partial draft, sign out and back in, and resume.
An owner can explicitly confirm all five required categories; missing and
invalid values fail. Changing scope or deleting the case invalidates
and erases facts. An unrelated account receives 404. No identity, address,
free-text or unexpected field is accepted. Review status never claims an
administrative determination.
