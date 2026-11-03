# Scenario 10 — Full End-to-End Journey: Resumption, Failures, Review, Results, and Official Handoff

**Scenario ID:** `PP-S10`  
**Area:** e2e, resilience, localization, evidence, application-package, audit  
**Type:** End-to-end plus positive, negative, edge, and security variants  
**Fixture policy:** Synthetic data; no real accounts, government submissions, or production personal documents  
**Administrative reference date:** 2026-11-02 (revalidate official material before production use)

## 1. User story

**Persona:** Amira (fictional), foreign citizen already registered in another Italian municipality, moving alone to Milan.

**User request:** > Please handle the paperwork for my move to Milan, explain it in English, and prepare a package I can review.

**Goal:** Demonstrate complete product value with all components, robust failure recovery, evidence-backed package and correct handoff/receipt handling.

## 2. Test setup and fixtures

- **Preconditions:** User has verified account; approved resident-in-Italy rules; synthetic valid housing documents; deterministic source and model fixtures; staging-like environment.
- **Synthetic input data:** previous registered city: Bologna (fixture); new address: Milan (fictional); housing basis: rental; move date: 2026-10-29; locale: en; model outage injected mid-run; fake submission receipt initially absent.
- **System components:** Next.js UI, FastAPI case API, LangGraph agent, reviewed rule engine, government RAG retrieval when relevant, private document processing, PostgreSQL case store.
- **Mock boundaries:** Model responses, government pages, notification delivery, portal clicks, and any external tools. Do not perform real-world actions.
- **Clock:** Freeze at `2026-11-02T10:00:00+01:00` unless a variant explicitly changes time.

## 3. Main test journey

| Step | User/system action | Required agent/application behavior | Expected state |
|---:|---|---|---|
| 1 | Authenticate and create case | One case created with correct owner and initial state | `draft` |
| 2 | Agent asks nationality, previous registration, new address, move date | Collect only missing relevant facts; verified state preserved | `intake` |
| 3 | Select resident-moving-from-Italian-municipality route | Use approved route; do not conflate first-arrival procedure | `procedure_selected` |
| 4 | Run rules and RAG lookups | Approved requirements + exact source citations surfaced | `requirements_ready` |
| 5 | Upload rental contract and supported ID document | Secure processing with source-linked extracted fields | `documents_review` |
| 6 | Inject transient LLM timeout | User sees non-destructive retry state; no lost facts | `recoverable_error` |
| 7 | User logs out and returns later | Authentication required; case and prior progress restored | `resumed` |
| 8 | Review extracts and correct one field | Corrections audited; checklist and package recalculated | `verified` |
| 9 | Prepare bilingual review package | Human-readable instructions, evidence list, unresolved risks, and source versions | `package_ready` |
| 10 | User approves package | Approval tied to exact version; no auto government submission | `submission_ready` |
| 11 | Open approved government handoff | Official portal shown; local state `handoff_opened`, not `submitted` | `handoff_opened` |
| 12 | User later enters official reference and attaches mock receipt | Store user-reported submission with explicit verification status; do not claim official validation | `submitted_user_reported` |
| 13 | Generate final case summary and export | Summarize verified prep, user-reported events, evidence and outstanding follow-up | `results_generated` |

## 4. Automated test variants and expected outcomes

| Test ID | Variation / trigger | Expected outcome and assertions |
|---|---|---|
| `PP-S10-J1` | Happy path to approved package | Checklist, extracted fields, cited report and official portal handoff produced. |
| `PP-S10-J2` | LLM timeout halfway through intake | Resume same case; retry with bounded attempts; no duplicate questions/actions. |
| `PP-S10-J3` | Database write conflict | Reject stale write or reconcile safely; no lost user correction. |
| `PP-S10-J4` | User changes supported-language setting | English/Italian outputs change without altering fact values or citations. |
| `PP-S10-J5` | Missing mandatory document at final review | Package remains blocked and identifies exact missing evidence. |
| `PP-S10-J6` | Approved rule version updates before submission | Invalidate stale approval and require re-review of affected claims. |
| `PP-S10-J7` | Fake government receipt text without actual evidence | Record as unverified user report only, not official confirmation. |
| `PP-S10-J8` | Official portal unavailable | Show retry/verified link information; preserve ready package. |
| `PP-S10-J9` | User retries submit click | Never auto-submit or change case to formally submitted. |
| `PP-S10-J10` | User downloads results | Export excludes secrets, includes verified citations and correct state semantics. |
| `PP-S10-J11` | User abandons after upload | Secure session expiry and retention rules apply; resume only after authentication. |
| `PP-S10-J12` | New source becomes unapproved during final review | Block stale critical content; request human source approval. |

## 5. Required assertions

- [ ] Exported final report distinguishes **prepared**, **user-approved**, **handoff opened**, **user-reported submitted** and **officially confirmed** (only if independently verified).
- [ ] Full Playwright journey passes with fixture source registry and intercepted external links.
- [ ] Report includes summary, checklist, known facts, evidence, citations, revision history, and next steps without unsupported legal certainty.
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
- `MIL-RENT` — https://servizicrm.comune.milano.it/centro-supporto/KA-00329/Residenza-stranieri-in-affitto-documenti-immobile
- `MIL-FAQ` — https://servizicrm.comune.milano.it/centro-supporto/KA-00330/Richiestacambio-residenza-come-procedere
- `MIL-TARI` — https://servizicrm.comune.milano.it/centro-supporto/KA-02121/Termine-dichiarazione-Tari-per-nuova-occupazione

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

- [ ] Main journey for `PP-S10` passes in a disposable test environment.
- [ ] All listed variants have test implementations or a tracked reason why a test is blocked.
- [ ] Critical negative, permission, grounding, and incorrect-completion assertions pass.
- [ ] Evidence artifacts are linked from CI or the test run; no private data is embedded in committed fixtures.
- [ ] A reviewer confirms no unsupported administrative rule is treated as accepted simply because retrieval returned it.
- [ ] New failures become permanent regression tests.
