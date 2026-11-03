# Scenario 02 — Happy Path: Milan-to-Milan Residence Change and Application Package

**Scenario ID:** `PP-S02`  
**Area:** intake, rules, rag, document, checklist, package, handoff  
**Type:** End-to-end plus positive, negative, edge, and security variants  
**Fixture policy:** Synthetic data; no real accounts, government submissions, or production personal documents  
**Administrative reference date:** 2026-11-02 (revalidate official material before production use)

## 1. User story

**Persona:** Marco Bianchi (fictional), Italian, registered in Milan, sole tenant, moving to another Milan apartment.

**User request:** > I changed my flat inside Milan. Prepare everything I need for the residence change.

**Goal:** Produce a personalized, evidence-linked application-review package and official handoff without making a submission claim.

## 2. Test setup and fixtures

- **Preconditions:** Verified user with valid session; `MIL-RES` and relevant approved housing rules seeded; correctly formatted synthetic lease PDF; mock official portal endpoint.
- **Synthetic input data:** case: PP-CASE-002; old address: Via Example 1, Milan (fictional); new address: Via Sample 20, Milan (fictional); move date: 2026-10-25; lease tenant: Marco Bianchi.
- **System components:** Next.js UI, FastAPI case API, LangGraph agent, reviewed rule engine, government RAG retrieval when relevant, private document processing, PostgreSQL case store.
- **Mock boundaries:** Model responses, government pages, notification delivery, portal clicks, and any external tools. Do not perform real-world actions.
- **Clock:** Freeze at `2026-11-02T10:00:00+01:00` unless a variant explicitly changes time.

## 3. Main test journey

| Step | User/system action | Required agent/application behavior | Expected state |
|---:|---|---|---|
| 1 | Starts new case and selects residence change | Agent identifies Milan internal move and verifies procedure applicability | `procedure_selected` |
| 2 | Answers who is moving, move date, housing basis | Stores confirmed facts; asks only missing required fields | `intake_in_progress` |
| 3 | Agent calls requirements evaluator | Gets approved conditional requirements, not just RAG guesses | `requirements_calculated` |
| 4 | Agent searches government knowledge | Retrieves approved Milan evidence with passage IDs and source versions | `evidence_attached` |
| 5 | Uploads clean synthetic rental agreement | Secure upload; document recognized; fields extracted with source spans | `document_processed` |
| 6 | Reviews extracted tenant and address | User confirms fields; reconciles with case values | `document_verified` |
| 7 | Opens checklist | Required items, conditional items, explanatory sources and TARI follow-up visible | `checklist_generated` |
| 8 | Chooses Prepare application | Package generated from approved fields; no unknown mandatory values | `review_ready` |
| 9 | Reviews package, confirms accuracy | Review records user confirmation and version hash | `submission_ready` |
| 10 | Opens official handoff | Verified official portal instructions shown; case remains NOT submitted | `handoff_opened` |

## 4. Automated test variants and expected outcomes

| Test ID | Variation / trigger | Expected outcome and assertions |
|---|---|---|
| `PP-S02-B1` | All required data and supported documents provided | `submission_ready` package with verified fields and citations; no submission status. |
| `PP-S02-B2` | Document field differs from user intake | Block package, show side-by-side discrepancy and ask for correction. |
| `PP-S02-B3` | User edits date after checklist generation | Recompute applicable timeline and invalidate stale package approval. |
| `PP-S02-B4` | Same package generation requested twice | Single active version or documented new version; no silent duplication. |
| `PP-S02-B5` | RAG returns irrelevant city source | Exclude unsupported jurisdiction; do not cite it for Milan requirements. |
| `PP-S02-B6` | Official portal unreachable | Retain ready package, show safe retry or official guidance; never claim submission. |
| `PP-S02-B7` | User declines to confirm extracted field | Draft stays in review; no auto confirmation. |
| `PP-S02-B8` | Missing mandatory input | Required item remains blocked and is clearly explained. |

## 5. Required assertions

- [ ] Official Milano guidance describes a 20-day notification period for residence change: show only when confirmed from approved source version.
- [ ] TARI is a related separately tracked obligation; do not claim it is included in residence filing.
- [ ] Outputs should include checklist, package summary, document evidence map, source references, and official handoff.
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

- [ ] Main journey for `PP-S02` passes in a disposable test environment.
- [ ] All listed variants have test implementations or a tracked reason why a test is blocked.
- [ ] Critical negative, permission, grounding, and incorrect-completion assertions pass.
- [ ] Evidence artifacts are linked from CI or the test run; no private data is embedded in committed fixtures.
- [ ] A reviewer confirms no unsupported administrative rule is treated as accepted simply because retrieval returned it.
- [ ] New failures become permanent regression tests.
