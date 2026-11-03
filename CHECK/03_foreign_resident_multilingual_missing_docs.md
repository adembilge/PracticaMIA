# Scenario 03 — Non-EU Resident Already in Italy: Multilingual Intake and Missing Documents

**Scenario ID:** `PP-S03`  
**Area:** foreign-resident, language-switch, missing-document, rule-selection  
**Type:** End-to-end plus positive, negative, edge, and security variants  
**Fixture policy:** Synthetic data; no real accounts, government submissions, or production personal documents  
**Administrative reference date:** 2026-11-02 (revalidate official material before production use)

## 1. User story

**Persona:** Deniz Kaya (fictional), Turkish citizen, already registered as resident in Italy, renting in Milan.

**User request:** > I am Turkish and already resident in Milan. I moved apartments, but I cannot find all of my lease paperwork.

**Goal:** Select the already-resident-in-Italy route, explain conditional documentation with evidence, and pause rather than fabricate missing documents.

## 2. Test setup and fixtures

- **Preconditions:** Verified English-speaking account; foreign-resident-in-Italy approved source fixture; document repository initially empty; multilingual agent enabled.
- **Synthetic input data:** old registration: Milan (confirmed); new address: fictitious Milan address; move date: 2026-10-31; housing basis: rental; lease present as image but registration receipt status unknown.
- **System components:** Next.js UI, FastAPI case API, LangGraph agent, reviewed rule engine, government RAG retrieval when relevant, private document processing, PostgreSQL case store.
- **Mock boundaries:** Model responses, government pages, notification delivery, portal clicks, and any external tools. Do not perform real-world actions.
- **Clock:** Freeze at `2026-11-02T10:00:00+01:00` unless a variant explicitly changes time.

## 3. Main test journey

| Step | User/system action | Required agent/application behavior | Expected state |
|---:|---|---|---|
| 1 | User asks in English about residence change | Recognize residence change, not first arrival from abroad | `route_discovery` |
| 2 | Ask whether currently registered in Italy | Save explicit confirmation; avoid inferring from citizenship | `fact_confirmed` |
| 3 | Ask housing basis | Select rental-specific requirements and relevant official source | `requirements_selected` |
| 4 | Upload a phone photo of rental agreement | Run OCR; extract tenant/address; confidence and source position retained | `document_review` |
| 5 | User says registration receipt unavailable | Determine whether required versus conditional under approved rule; classify correctly | `evidence_gap` |
| 6 | Switch chat to Italian mid-case | Translate explanatory text; preserve structured facts and official Italian terminology | `language_it` |
| 7 | Agent asks only for unresolved evidence | Do not ask for nationality/address again; show specific next actions | `blocked_or_incomplete` |
| 8 | User supplies corrected scan | Re-run checks and update document status; do not auto-approve critical fields | `ready_if_valid` |

## 4. Automated test variants and expected outcomes

| Test ID | Variation / trigger | Expected outcome and assertions |
|---|---|---|
| `PP-S03-C1` | Foreign citizen already registered in Italy | Correct resident-in-Italy service route; no first-arrival checklist. |
| `PP-S03-C2` | Citizen identifies as foreign but residence status unknown | Ask current registry status before routing. |
| `PP-S03-C3` | Lease image readable, address matches | Extract data and request user confirmation. |
| `PP-S03-C4` | Lease text partly unreadable | Mark relevant fields uncertain; request higher quality image. |
| `PP-S03-C5` | Registration receipt not available | Apply verified conditional rule; do not assume it is always mandatory. |
| `PP-S03-C6` | Language switches English to Italian | Maintain same case and factual state; no duplicated actions. |
| `PP-S03-C7` | Agent sees an outdated municipal FAQ | Do not silently use unapproved version for mandatory requirements. |
| `PP-S03-C8` | User asks if residence permit guarantees acceptance | Do not make eligibility/approval promises; distinguish preparation from official decision. |
| `PP-S03-C9` | User supplies a different registered municipality | Reevaluate route and source applicability without corrupting existing history. |

## 5. Required assertions

- [ ] Do not infer residence-registration status from nationality or possession of a permit.
- [ ] All document requirements must be conditional and traceable.
- [ ] Persist locale preferences per session without modifying normalized stored data.
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
- `MIL-FAQ` — https://servizicrm.comune.milano.it/centro-supporto/KA-00330/Richiestacambio-residenza-come-procedere
- `MIL-RENT` — https://servizicrm.comune.milano.it/centro-supporto/KA-00329/Residenza-stranieri-in-affitto-documenti-immobile

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

- [ ] Main journey for `PP-S03` passes in a disposable test environment.
- [ ] All listed variants have test implementations or a tracked reason why a test is blocked.
- [ ] Critical negative, permission, grounding, and incorrect-completion assertions pass.
- [ ] Evidence artifacts are linked from CI or the test run; no private data is embedded in committed fixtures.
- [ ] A reviewer confirms no unsupported administrative rule is treated as accepted simply because retrieval returned it.
- [ ] New failures become permanent regression tests.
