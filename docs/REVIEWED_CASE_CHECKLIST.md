# Signed first-route checklist — MVP integration

## User journey

1. Sign in, create a saved example case, complete the five product scope questions.
2. Enter a separate **fictional** structured case intake and explicitly confirm all five categorical facts. The existing optional move date is saved but does not drive eligibility or deadline calculations.
3. The saved-case workspace requests `GET /api/cases/{id}/checklist`, a protected Next.js Auth0 proxy to `GET /api/v1/cases/{id}/checklist`.
4. The FastAPI backend retrieves the authenticated owner's case and confirmed intake from Neon. Client-provided facts or rule IDs are never accepted.
5. Only the exact owner-reviewed first Milan rule catalog can issue actions. It has a previously recorded owner review, a technical Ed25519 signature, and a **pinned public key** matching `requirements/milan-residence-change/review_public_key_v1.b64`. The signing private key is not in the repository or runtime.
6. Every exact citation is dynamically resolved against the **approved active source version, append-only approval event, raw snapshot digest, and passage integrity**. A missing/revoked/changed passage or mismatched original URL blocks the whole checklist.
7. Five signed action descriptions (unaltered English from the catalog) appear with individual official links, source versions and review dates. An older ANPR PDF is clearly labelled archived and **not** necessarily current.
8. All actions are `needs_user` and never `verified` or `submitted`. No mandatory document categories are invented. TARI is explicitly described in its signed text as a separate check, not a mandatory residence attachment.

## Exact release boundary

- Supported only: **one adult Italian citizen already registered in Italy, moving alone into Comune di Milano, as holder of a registered private rental contract**, with no household aggregation.
- Other confirmed categories yield `outside_first_route` with **zero** actions.
- Unfinished scope or unconfirmed/unknown intake yields `needs_scope` or `needs_confirmation` with **zero** actions.
- Bad signature, incomplete catalog or missing/revoked official source produces `evidence_unavailable` with **zero** actions.
- No personal eligibility decision, record verification, document verification, submitted application, official deadline calculation or unsupported proof substitution occurs.
- The existing Preview `PREPARATION_RULE_REVIEW_PUBLIC_KEY` setting and legacy Preview rule gate remain unchanged. The public key is pinned **only for this first pre-reviewed catalog**, and tested against the committed reviewed key. Updating the rules requires another human review and cryptographic re-signing.

## Testing and deployment

- Backend tests: authenticated owner isolation, missing intake, user confirmation, five signed actions, invalidation on scope edits, unsupported tenancy, citation revocation, malicious URL and public-key signature tampering.
- Frontend tests: five expected rule IDs, version and URL allowlists, no invented attachment categories, no malicious citation URL, and blocked states with no instructions.
- Both GitHub Actions test/build pipelines must pass. No Vercel testing, sandbox or deployment requests.
- The endpoint reads the existing `20261109_0014` Neon schema; **no new database migration**.
- Merging on GitHub does **not** prove the current Vercel-hosted production website has deployed this code. Browser E2E and a separate production release remain necessary.

## Beyond this milestone

Checklist action state is **not yet persisted as user-completed**. These are source-backed actions presented for manual review, not a completed application checklist or a generated package. A later milestone should add owner-controlled progress with reset on facts/rules/source changes and complete document-review and package-generation steps.
