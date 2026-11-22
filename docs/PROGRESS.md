# Progress and release status

**Last updated:** 22 November 2026

## Current product surface

The customer root route is being consolidated into one chat shell. Legacy case and synthetic demo pages are being removed in the current cleanup PR. The intended customer navigation is conversation history only.

The conversation transport and worker are still restricted to isolated development/Preview infrastructure. Production chat execution is not enabled. No deployment, live Auth0 journey or production acceptance is claimed by the source cleanup.

## Phase 4

- Task 34.6: bilingual authority spelling suggestions remain confirmation-only; exact-name/near-match collisions remain ambiguous. PR #244 merged as `27f853507e9f48caea2ecb506cb42738382793d`.
- Next: Task 35.1 clarification context check.
- Phase 5 remains paused.

## Verification boundaries

Backend and frontend CI results apply to their tested revisions and environments. Synthetic fixtures do not establish participant evidence, live legal validation, broad municipal coverage or production readiness. Real personal-document upload remains disabled pending independent privacy and operational reviews.

See [active work](ACTIVE_WORK.md), [acceptance status](ACCEPTANCE_TESTING.md), and [product specification](PRODUCT_SPECIFICATION.md).
