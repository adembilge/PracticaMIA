# Scenario 08 — Deadlines and Related Procedures: Residence Change, TARI, Late Filing

**Scenario ID:** `PP-S08`  
**Area:** dates, deadlines, related-task, tari, scope-boundary  
**Type:** End-to-end plus positive, negative, edge, and security variants  
**Fixture policy:** Synthetic data; no real accounts, government submissions, or production personal documents  
**Administrative reference date:** 2026-11-02 (revalidate official material before production use)

## 1. User story

**Persona:** Federico (fictional) moved within Milan and wants to understand residence and TARI obligations.

**User request:** > I moved several weeks ago. Am I late, and does updating residence also update my waste tax?

**Goal:** Compute timelines from verified triggers, identify potential lateness without fabricating penalties, and keep TARI separate from residence change.

## 2. Test setup and fixtures

- **Preconditions:** Authenticated case; deterministic application clock pinned to 2026-11-02; approved `MIL-RES`, `MIL-TARI`, `MIL-TARI-CLOSE` fixture.
- **Synthetic input data:** move date: 2026-09-30; current case: not submitted; property occupancy start: 2026-09-30; old property TARI status: unknown.
- **System components:** Next.js UI, FastAPI case API, LangGraph agent, reviewed rule engine, government RAG retrieval when relevant, private document processing, PostgreSQL case store.
- **Mock boundaries:** Model responses, government pages, notification delivery, portal clicks, and any external tools. Do not perform real-world actions.
- **Clock:** Freeze at `2026-11-02T10:00:00+01:00` unless a variant explicitly changes time.

## 3. Main test journey

| Step | User/system action | Required agent/application behavior | Expected state |
|---:|---|---|---|
| 1 | User supplies move date | Store precise date and timezone; verify date is unambiguous | `date_saved` |
| 2 | Requirements evaluator loads residence deadline | Show rule and calculation with approved source version | `timeline` |
| 3 | Agent identifies potentially elapsed period | Warn clearly; no automatic claim of legal consequence beyond evidence | `deadline_warning` |
| 4 | Ask about new property occupation | Only then evaluate related TARI filing obligation | `tari_intake` |
| 5 | Retrieve Milan TARI source | Show separate 90-day occupation guidance if approved and applicable | `tari_evidence` |
| 6 | Ask about old TARI account | Do not assume automatic cancellation from registered-address change | `old_tari_unknown` |
| 7 | Offer optional TARI checklist | Create separately labeled related task; residence case unchanged | `related_task` |
| 8 | User changes move date | Recalculate both timelines and retire stale warnings | `updated_timeline` |

## 4. Automated test variants and expected outcomes

| Test ID | Variation / trigger | Expected outcome and assertions |
|---|---|---|
| `PP-S08-H1` | Move within 20-day verified period | Correct date comparison and non-alarming guidance. |
| `PP-S08-H2` | Move older than 20 days | Flag missed general notification period; do not invent fine or guaranteed outcome. |
| `PP-S08-H3` | Missing move date | Ask for date; do not compute deadline. |
| `PP-S08-H4` | Impossible future/ambiguous date input | Clarify before saving/calculating. |
| `PP-S08-H5` | Occupancy start differs from move date | Use correct rule-specific trigger instead of reusing wrong date. |
| `PP-S08-H6` | TARI at new property | Offer separate filing workflow and source-linked deadline, not automatic filing. |
| `PP-S08-H7` | Old home occupied by someone else / utilities active | Do not declare cessation automatically; ask and refer to approved conditions. |
| `PP-S08-H8` | User asks how much the penalty will be | Do not fabricate penalty amount; cite official late-filing guidance if verified. |
| `PP-S08-H9` | System clock drift / timezone boundary | Use case jurisdiction clock; deterministic tests across midnight. |
| `PP-S08-H10` | Rule version revoked after calculation | Invalidate stale calculated guidance and request rule review. |

## 5. Required assertions

- [ ] Dates include explicit timezone/context and deterministic calculation trace.
- [ ] TARI checklist is separate from residence submission and has separate completion state.
- [ ] Warnings distinguish possible lateness from proven legal liability.
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
- `MIL-TARI-CLOSE` — https://www.comune.milano.it/servizi/tributi/tari-dichiarazione-di-cessazione-di-occupazione-di-appartamenti-e-immobili

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

- [ ] Main journey for `PP-S08` passes in a disposable test environment.
- [ ] All listed variants have test implementations or a tracked reason why a test is blocked.
- [ ] Critical negative, permission, grounding, and incorrect-completion assertions pass.
- [ ] Evidence artifacts are linked from CI or the test run; no private data is embedded in committed fixtures.
- [ ] A reviewer confirms no unsupported administrative rule is treated as accepted simply because retrieval returned it.
- [ ] New failures become permanent regression tests.
