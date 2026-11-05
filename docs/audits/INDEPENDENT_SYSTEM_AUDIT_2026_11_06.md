# PracticaMIA — independent adversarial system audit
**Audit date:** 6 November 2026 (Europe/Rome)  
**Scope:** repository at PR #31, anonymous real Vercel production routes,
isolated Neon staging, and disposable synthetic CI databases.

## Executive verdict

**NOT release-ready for real administrative advice.**

The available prototype's core security boundaries passed substantial new
tests, and the audit identified three concrete implementation weaknesses
which were corrected in this PR. However, the full product specified in
`PracticaMIA_Complete_Project_Specification.md` does **not yet exist**:
verified deterministic administrative rules, user document extraction,
complete LangGraph agent orchestration, reviewed application packages, and
real authenticated end-to-end journeys remain unimplemented or unverified.
Do not confuse a green unit-test suite with product completion.

## Testing evidence

| Type | Work performed | Observed result |
| --- | --- | --- |
| **Real Vercel HTTP** | Single anonymous GET against 10 public/denied routes from an independent GitHub runner | **10/10 passed** |
| **Backend API/unit** | Signed synthetic JWT cases; malicious payloads, cross-user read/write/delete, provenance mutations | **190 passed** |
| **PostgreSQL integration** | PG17 + pgvector; migrations; approved/revoked evidence; 12 parallel model-budget reservations | **10 passed** |
| **Frontend unit** | 243 state-machine combinations, strict dates, malicious origins, tampered reviewer payloads | **23 passed** |
| **Compiled frontend HTTP** | Built Next.js served over actual localhost HTTP, no Auth0 credentials | **2 passed** |
| **Neon staging read-only invariants** | Snapshot sizes, body digests, extraction/passage digests, offsets | **13/13 snapshot versions valid, 50 passages** |
| **Neon staging metadata migration** | Additive revision 0010 backfilled metadata checksums | **13/13 metadata digests valid** |

Test counts are counts of CI cases, not unique vulnerabilities. One frontend
test covers all 243 combinations. A stress test has only 12 simultaneous
requests and is NOT a production-scale load benchmark.

- [Independent production GET audit, all 10 passing](https://github.com/adembilge/PracticaMIA/actions/runs/42130290736)
- [Audit implementation PR #31](https://github.com/adembilge/PracticaMIA/pull/31)
- [Independent source review evidence tracking](https://github.com/adembilge/PracticaMIA/issues/28)
- [Staging-approved-only pgvector indexer](https://github.com/adembilge/PracticaMIA/pull/30)

### Live production observations

- `GET /` and `GET /account` returned HTTP 200. Rendered HTML had
  a document language, a main landmark, a title and mobile viewport metadata.
  This is a basic structural check, **not an accessibility certification**.
- `GET /knowledge/review`, preview assistant page, and browser-review
  proxy returned HTTP 404 as expected in production.
- Anonymous case listing returned HTTP 401 from both the frontend proxy
  and backend API. The backend review route returned HTTP 404.
- Backend `GET /health` returned HTTP 200 and an OK status.
- Backend `GET /openapi.json` returned HTTP 200. Decide whether publicly
  exposing API documentation matches the production threat model.
- Security headers were **absent** from live responses: at least
  `X-Content-Type-Options`, `Referrer-Policy`, and
  `Content-Security-Policy`. This PR adds MIME, referrer, anti-framing,
  and browser-device-permission headers in code; **they have NOT yet been
  observed on the production deployment**. CSP requires separate
  Next.js/Auth0 compatibility testing.
- Individual GET timing ranged from roughly 100–2300 ms across two runs.
  Only one request per path per run was made; no p95, sustained-throughput,
  regional latency, or cold-start conclusion can be drawn.

### Novel bugs discovered and corrected in PR #31

**1. Source metadata integrity was weaker than advertised.** Raw HTML/text
bytes and passages were SHA-256 checked, but changing a stored
`observed_title`, `observed_last_updated` or an alternate same-article
`observed_url` could still pass source verification. Added a second,
length-delimited SHA-256 of acquisition metadata, versioned schema migration
0010 with backfill, and negative mutation tests. This is internal drift
detection, **not** a municipal digital signature or cryptographic proof of
source authenticity.

**2. CSRF Origin parsed URL credentials.** A synthetic malformed Origin
value such as `https://evil.test@practicamia.vercel.app` could be considered
equivalent to the legitimate site's origin by the URL parser. Browser Origin
headers do not normally contain credentials, so this is a hardening flaw
rather than evidence of a practical session takeover. The guard now rejects
any username or password in Origin before comparing origins.

**3. Mobile review only showed 500 characters.** The reviewer queue
previously allowed selection and attestation without showing the full
captured article. Added an Auth0-proxied, hash-checked full-text preview and
made complete retrieval a prerequisite to selecting each article. This still
does not replace actual human applicability review.

**4. Header hardening.** Added safe response headers to FastAPI and Next.js,
including on error responses. This fixes the configuration in code; it will
only affect public production once frontend and backend deployments are
actually updated. Strict CSP is not in this change.

### Failure-state and data security coverage

- All 243 possible complete demo questionnaire states match the independent
  finite-state oracle in both Python and JavaScript.
- Multiple synthetic users cannot read, modify or delete the other user's
  saved cases. Nonexistent and foreign-owned case IDs share the same 404.
- Malicious over-posting of `owner_subject`, `status`, `approved`,
  `officially_confirmed`, or arbitrary procedure fields returns 422.
- Anonymous calls and unsupported credential schemes cannot read case data.
- Browser-review access remains reviewer-only; batch approval is atomic and
  excludes the historical PDF, and fake user role claims do not grant access.
- Snapshot provenance modifications invalidate integrity. Both snapshots
  and individual citation spans are hash checked.
- A synthetic 12-way PostgreSQL race does not exceed the configured
  shared per-user model request quota.
- The existing synthetic assistant tests check citation-bound quotation,
  wrong-case denial, model failure, usage limits, and immediate abstention
  after source revocation. No real provider was contacted.
- There was no permission to use real personal records and no production
  database writes were performed.

## Release blockers and explicitly untested areas

| Priority | Area | Status and why it matters |
| --- | --- | --- |
| **P0** | Live administrative accuracy | 12 browser captures + one older Allegato A are still pending; 0 approved versions and 0 real embeddings, so no real official-answer quality validation is possible |
| **P0** | Real workflow completeness | Rules engine, document upload/OCR, full agent graph, legally reviewed checklist and application package remain absent, not failed tests |
| **P1** | Real login and role-based E2E | No verified live Auth0 reviewer session, mobile approval or authenticated cross-account E2E through public preview. Local signed JWT fixtures do not replace it |
| **P1** | Environment alignment | Production frontend is behind main; production Neon schema `20261104_0002`, staging `20261106_0010`. Never point new knowledge API at the old production schema |
| **P1** | User-facing embeddings and model | Index planner is implemented but no provider key or embeddings; assistant still runs lexical search, and English-to-Italian retrieval quality remains unmeasured |
| **P1** | CSP/browser security | Code adds basic response headers, but production upgrade and CSP compatibility evaluation remain outstanding |
| **P1** | Concurrency/recovery | Multi-user API simultaneous edits, real user resumption, backup restore and network partition recovery have not been exercised end-to-end |
| **P2** | Accessibility | Basic HTML landmarks passed; no real screen-reader, keyboard, low-vision, or physical mobile-device study |
| **P2** | Performance & cost | A few anonymous GETs and 12 simulated parallel quota attempts are not a load test; cold starts, p95/p99, sustained load and provider cost remain unknown |
| **P2** | Provider privacy/legal review | External model data processing/retention, source correctness, and GDPR readiness require separate expert assessment |

The ten cross-functional scenarios in the project specification are
**specifications of desired tests**, not all executable workflows. In
particular scenarios 02–06 and 08–10 cannot currently pass true
production-like end-to-end acceptance because essential product features
have not been built. Reporting those as green would be misleading.

## Follow-up plan by outcome

1. **Before enabling any real AI guidance:** have an allowlisted reviewer
   inspect and approve each current municipal source; recheck 2025 FAQ
   exceptions and verify replacement PDFs. Keep the historical PDF pending
   until its currency is independently established.
2. **Before live preview:** align Vercel deployments with main, configure
   isolated staging Auth0, run a *real* two-account journey including a
   reviewer, and verify no source or token data leaks between sessions.
3. **Before release:** implement and test the actual rules engine and
   document workflow, evaluate bilingual retrieval with reviewed labels,
   verify prompt-injection resistance and privacy/data deletion, and
   exercise backups/restore, network-failure recovery and real mobile
   accessibility.
4. **After safe deployment:** repeat read-only production smoke to verify
   HTTP security headers and code versions; add a fully compatible CSP
   with nonce strategy before making privacy-sensitive flows public.

**Verdict:** tested and improved development foundation; **not yet a
complete, live, end-to-end verified government-assistance agent**.
