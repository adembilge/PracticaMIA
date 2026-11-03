# Scenario 05 — Shared Household: Host Consent, Adults, Conditional Requirements, and Dependencies

**Scenario ID:** `PP-S05`  
**Area:** household, lodging, consent, conditional-rules, blocked-checklist  
**Type:** End-to-end plus positive, negative, edge, and security variants  
**Fixture policy:** Synthetic data; no real accounts, government submissions, or production personal documents  
**Administrative reference date:** 2026-11-02 (revalidate official material before production use)

## 1. User story

**Persona:** Luca (fictional) moves to a Milan address already occupied by another person; another adult may join the case.

**User request:** > I will live with a friend who rents the apartment. How do I change my residence?

**Goal:** Ask conditional questions, identify applicable host/household consent requirements, and never invent another person’s approval.

## 2. Test setup and fixtures

- **Preconditions:** Authenticated user; approved hosting/source fixture; household facts unconfirmed; no automatic signature or third-party access.
- **Synthetic input data:** applicant: Luca Neri (fictional); host: user-supplied placeholder; new address: fictitious Milan dwelling; housing basis: guest; adult household count: unknown initially.
- **System components:** Next.js UI, FastAPI case API, LangGraph agent, reviewed rule engine, government RAG retrieval when relevant, private document processing, PostgreSQL case store.
- **Mock boundaries:** Model responses, government pages, notification delivery, portal clicks, and any external tools. Do not perform real-world actions.
- **Clock:** Freeze at `2026-11-02T10:00:00+01:00` unless a variant explicitly changes time.

## 3. Main test journey

| Step | User/system action | Required agent/application behavior | Expected state |
|---:|---|---|---|
| 1 | User states moving into friend’s home | Identify housing basis guest/host rather than renter | `housing_context` |
| 2 | Agent asks who holds occupancy rights | Save landlord/tenant/host relationship as confirmed fact | `conditional_branch` |
| 3 | Agent retrieves host-related requirements | Return approved official evidence for assent documentation | `requirements_selected` |
| 4 | User says host agrees verbally | Explain any verified evidence/form need; do not mark signed approval present | `pending_consent` |
| 5 | User indicates another adult is moving | Collect whether adult is applicant and appropriate consent/state | `multi_adult_case` |
| 6 | Checklist shows dependency | Host evidence and adult-related approvals block package if rules require them | `blocked_checklist` |
| 7 | Correct signed form uploaded | Extract names and signatures only as observed; request user review | `review` |
| 8 | User removes second adult from case | Recalculate requirements; preserve historical decisions with audit event | `updated_plan` |

## 4. Automated test variants and expected outcomes

| Test ID | Variation / trigger | Expected outcome and assertions |
|---|---|---|
| `PP-S05-E1` | Guest moving into rented apartment | Select hosting-related evidence according to approved Milan source. |
| `PP-S05-E2` | Owner provides consent but no document | Do not treat verbal assertion as a signed form; clarify what evidence is required. |
| `PP-S05-E3` | Host document names different address | Block and show document conflict. |
| `PP-S05-E4` | Second adult included | Collect relevant details and handle their required participation or authorization. |
| `PP-S05-E5` | Existing registered householder aggregation | Identify potential assent branch; do not impose it on all users. |
| `PP-S05-E6` | User uploads forged-looking signature | Do not declare authenticity; mark verification limits and request review. |
| `PP-S05-E7` | Host is not a PaperPilot user | Do not invite or contact the host without explicit user action and authorized integration. |
| `PP-S05-E8` | Household member removed | Regenerate checklist and invalidate obsolete approval assumptions. |
| `PP-S05-E9` | Minor is mentioned | Do not assume adult-signature rules for a minor; escalate unsupported family complexity. |

## 5. Required assertions

- [ ] Never manufacture third-party consent or impersonate another adult.
- [ ] Dependency graph keeps required approvals visible before package-ready status.
- [ ] Add explicit human approval gate where household applicability remains ambiguous.
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

- `MIL-HOST` — https://servizicrm.comune.milano.it/centro-supporto/KA-00367/
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

- [ ] Main journey for `PP-S05` passes in a disposable test environment.
- [ ] All listed variants have test implementations or a tracked reason why a test is blocked.
- [ ] Critical negative, permission, grounding, and incorrect-completion assertions pass.
- [ ] Evidence artifacts are linked from CI or the test run; no private data is embedded in committed fixtures.
- [ ] A reviewer confirms no unsupported administrative rule is treated as accepted simply because retrieval returned it.
- [ ] New failures become permanent regression tests.
