# Scenario 01 — New Account, Authentication, and First Administrative Case

**Scenario ID:** `PP-S01`  
**Area:** auth, onboarding, account-security, case-creation  
**Type:** End-to-end plus positive, negative, edge, and security variants  
**Fixture policy:** Synthetic data; no real accounts, government submissions, or production personal documents  
**Administrative reference date:** 2026-11-02 (revalidate official material before production use)

## 1. User story

**Persona:** Giulia Rossi (fictional), Italian citizen already resident in Milan; solo tenant moving within Milan.

**User request:** > I moved to a different flat in Milan and want to update my residence.

**Goal:** Establish a secure account and create exactly one linked case; answer should begin with intake, not invent submission.

## 2. Test setup and fixtures

- **Preconditions:** No user account; mocked verified email delivery; local identity provider; `MIL-RES` approved; app starts on English landing page.
- **Synthetic input data:** email: giulia01@example.test; password: stored only as a secure hash; old address: Milan fixture A; new address: Milan fixture B; move date: 2026-10-27; initial locale: en.
- **System components:** Next.js UI, FastAPI case API, LangGraph agent, reviewed rule engine, government RAG retrieval when relevant, private document processing, PostgreSQL case store.
- **Mock boundaries:** Model responses, government pages, notification delivery, portal clicks, and any external tools. Do not perform real-world actions.
- **Clock:** Freeze at `2026-11-02T10:00:00+01:00` unless a variant explicitly changes time.

## 3. Main test journey

| Step | User/system action | Required agent/application behavior | Expected state |
|---:|---|---|---|
| 1 | Guest opens product | Shows clear supported-task description, privacy notice, login/register actions | `landing` |
| 2 | Registers with test email and a strong password | Validates inputs; sends mock verification message; no profile/case until verified under chosen policy | `verification_pending` |
| 3 | Uses valid verification token | Account activated; one-time token invalidated | `active_account` |
| 4 | Signs in | Secure session issued; session token stored using approved mechanism | `authenticated` |
| 5 | Asks to change residence within Milan | Intent routed to supported residence-change case | `intent_recognized` |
| 6 | Confirms move date and individual applicant | Case saved with `draft/intake` status and owner ID | `case_created` |
| 7 | Opens dashboard and reloads | Same case persists once, with progress and next question | `intake` |
| 8 | Logs out and tries protected case URL | Redirects to authentication; protected content unavailable | `logged_out` |

## 4. Automated test variants and expected outcomes

| Test ID | Variation / trigger | Expected outcome and assertions |
|---|---|---|
| `PP-S01-A1` | Valid registration and verification | New verified account; one authenticated session; one user-owned draft case. |
| `PP-S01-A2` | Duplicate email registration | No duplicate account; generic response that does not enable email enumeration. |
| `PP-S01-A3` | Wrong password five times | Authentication denied; rate limiting or equivalent abuse control; no case data exposed. |
| `PP-S01-A4` | Expired and replayed verification token | Invalid token rejected; no duplicate activation; safe reissue path. |
| `PP-S01-A5` | Expired session during draft creation | No anonymous write; user reauthenticates and resumes without duplicate case. |
| `PP-S01-A6` | Browser refresh and second tab | Persisted case state stays consistent; idempotent creation on retries. |
| `PP-S01-A7` | Direct access to protected endpoint unauthenticated | 401/redirect; no user profile or case details returned. |
| `PP-S01-A8` | Registration fields with XSS and invalid email | Input rejected/escaped; no script executed or harmful markup rendered. |
| `PP-S01-A9` | Switch language before authentication | UI and prompts localize; account/case data remain intact. |

## 5. Required assertions

- [ ] Password never appears in logs or API response; verification tokens expire and are single use.
- [ ] Case creation requires an authenticated owner and is idempotent under retry.
- [ ] User obtains a source-grounded outline, never a fabricated approved application.
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

- [ ] Main journey for `PP-S01` passes in a disposable test environment.
- [ ] All listed variants have test implementations or a tracked reason why a test is blocked.
- [ ] Critical negative, permission, grounding, and incorrect-completion assertions pass.
- [ ] Evidence artifacts are linked from CI or the test run; no private data is embedded in committed fixtures.
- [ ] A reviewer confirms no unsupported administrative rule is treated as accepted simply because retrieval returned it.
- [ ] New failures become permanent regression tests.
