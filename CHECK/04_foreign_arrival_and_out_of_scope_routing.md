# Scenario 04 — Different Procedure: Arriving from Abroad, Unsupported Cases, and Safe Handoff

**Scenario ID:** `PP-S04`  
**Area:** scope-control, routing, source-conflict, first-arrival  
**Type:** End-to-end plus positive, negative, edge, and security variants  
**Fixture policy:** Synthetic data; no real accounts, government submissions, or production personal documents  
**Administrative reference date:** 2026-11-02 (revalidate official material before production use)

## 1. User story

**Persona:** Sara Haddad (fictional), non-EU citizen who recently arrived from abroad and has never registered residence in Italy.

**User request:** > I just arrived in Milan from another country. Can I use the normal ANPR change-of-address flow?

**Goal:** Detect distinct service route; set case `unsupported_needs_handoff` rather than prepare an incorrect standard residence-change package.

## 2. Test setup and fixtures

- **Preconditions:** User authenticated; approved source fixtures for standard change-of-residence and foreign citizens arriving from abroad; MVP supports only already-registered individual address changes.
- **Synthetic input data:** citizenship: non-EU synthetic; previous registry: outside Italy; arrival: 2026-10-28; prior Italian registered address: none.
- **System components:** Next.js UI, FastAPI case API, LangGraph agent, reviewed rule engine, government RAG retrieval when relevant, private document processing, PostgreSQL case store.
- **Mock boundaries:** Model responses, government pages, notification delivery, portal clicks, and any external tools. Do not perform real-world actions.
- **Clock:** Freeze at `2026-11-02T10:00:00+01:00` unless a variant explicitly changes time.

## 3. Main test journey

| Step | User/system action | Required agent/application behavior | Expected state |
|---:|---|---|---|
| 1 | User describes arrival from abroad | Request current registration history and citizenship where relevant | `clarification` |
| 2 | User confirms never registered in Italy | Determine that internal-change MVP does not apply | `out_of_scope` |
| 3 | Retrieve official Milan first-arrival service | Present verified authoritative alternative with citation | `evidence_returned` |
| 4 | Explain difference from standard route | Avoid mixing checklists or claiming a complete legal determination | `safe_guidance` |
| 5 | Offer official link and save notes | User can open authoritative service; PaperPilot does not submit | `handoff_only` |
| 6 | User attempts normal package generation | Deny as unsupported; retain explanation and user data | `blocked` |

## 4. Automated test variants and expected outcomes

| Test ID | Variation / trigger | Expected outcome and assertions |
|---|---|---|
| `PP-S04-D1` | Non-EU newcomer arriving from abroad | Redirect to dedicated Milan service and mark normal change flow unsupported. |
| `PP-S04-D2` | EU citizen arriving from abroad | Do not assume route equals resident-in-Italy change; check official dedicated guidance and scope. |
| `PP-S04-D3` | Italian AIRE returnee | Recognize special route mentioned by Milan; if not in MVP, offer sourced handoff. |
| `PP-S04-D4` | Applicant registered in another Italian municipality | Eligible route may differ from first arrival; use approved matrix and do not overblock. |
| `PP-S04-D5` | User refuses to say previous registration | Ask clarification; keep route unresolved instead of guessing. |
| `PP-S04-D6` | No approved source for alternative route | Say no verified guidance available; do not invent destination or link. |
| `PP-S04-D7` | User insists assistant submit anyway | Refuse unsupported submission; no external state change. |
| `PP-S04-D8` | Conflicting source snapshots | Block routing decision if material; surface evidence and require source review. |

## 5. Required assertions

- [ ] At no point construct a standard-residence application for the newcomer fixture.
- [ ] Unsupported case can be saved, exported and safely resumed.
- [ ] Source references include city, procedure and approved version.
- [ ] Every expected state is persisted consistently and exposed to the UI without claiming a later state.
- [ ] Agent trace contains tool names, inputs with sensitive fields redacted, output/status, retries, and failure reasons.
- [ ] Re-running the deterministic fixtures produces equivalent decisions; model variability does not bypass safety rules.
- [ ] At least one negative/blocked path is exercised in CI, not only the happy path.

## 6. Suggested automated coverage

| Layer | Examples |
|---|---|
| Unit tests (`pytest`) | Data validation, rule branches, state transitions, source approval, date logic where applicable |
| API integration (`pytest`) | Auth/session, tenant isolation, case/document CRUD, persisted revisions, tool authorization |
| Agent evaluations | Scenario-specific intent and tool decisions, correct abstention, grounded outputs, failure recovery |
| Browser E2E (`Playwright`) | User inputs, dialogs, error states, page refresh, result viewing and official handoff |
| Security/adversarial | Injection attempts, cross-user access, malicious file variants, unauthorized state changes |

## 7. Official-source anchors and fixture policy

These are **source anchors for reviewers and test-fixture provenance**, not blanket assertions that the same rule applies to every user. The code must use approved, versioned passages and rules, with conditions reviewed independently. No live portal submission is permitted in tests.

- `MIL-RES` — https://www.comune.milano.it/servizi/anagrafe/cambio-di-residenza
- `MIL-FOREIGN` — https://www.comune.milano.it/servizi/anagrafe/richiesta-di-residenza-per-persone-straniere-provenienti-dall-estero
- `MIL-FOREIGN-DOC` — https://www.comune.milano.it/servizi/anagrafe/richiesta-di-residenza-per-persone-straniere-provenienti-dall-estero/modulistica-richiesta-di-residenza-per-persone-straniere-provenienti-dall-estero
- `MIL-FAQ` — https://servizicrm.comune.milano.it/centro-supporto/KA-00330/Richiestacambio-residenza-come-procedere

## How to run this scenario

- **Automated layers:** `pytest` for API/rule/tool logic; LangGraph agent evaluations with recorded or mocked model responses; Playwright for browser flows; database assertions for persistence and audit events. Replace these conceptual commands with actual repository commands once implemented.
- **Isolation:** Start with a disposable database, unique synthetic user IDs, deterministic clock, stubbed email/model/government integrations, and a seeded, reviewed source-version fixture. No test may contact or submit to a live government portal.
- **Evidence:** For every assertion, record test ID, input fixture version, ruleset version, model identifier where relevant, tool trace, result, and failure screenshot/log with personal fields redacted.
- **Status model:** `PASS` requires every mandatory assertion. `FAIL` records observed versus expected behavior. `BLOCKED` means an external approval or unverified government rule prevents a valid conclusion; it is not a pass.

## Product-wide invariants

1. **Never claim an official submission occurred** without an independently provided, explicitly confirmed official receipt; a handoff link or uploaded draft is not submission.
2. Administrative requirements and deadlines originate from **approved, versioned rules** linked to official source evidence; raw retrieved text is informative evidence, not self-approving rule data.
3. The agent must distinguish **unknown**, **not applicable**, **missing document**, and **contradictory evidence**. It must not fill unknown personal fields with guesses.
4. No cross-account reading, mutation, document access, or retrieval of private source data. Do not send secrets or unnecessary personal data to model calls or logs.
5. Every consequential extracted field and pre-submission package must be reviewable and correctable by the user. External actions and government authentication stay under user control.
6. Run with **synthetic identities and documents only**. Any example identifiers, addresses, and receipts below are fictional test fixtures, not real people or real official identifiers.


## 8. Definition of done

- [ ] Main journey for `PP-S04` passes in a disposable test environment.
- [ ] All listed variants have test implementations or a tracked reason why a test is blocked.
- [ ] Critical negative, permission, grounding, and incorrect-completion assertions pass.
- [ ] Evidence artifacts are linked from CI or the test run; no private data is embedded in committed fixtures.
- [ ] A reviewer confirms no unsupported administrative rule is treated as accepted simply because retrieval returned it.
- [ ] New failures become permanent regression tests.
