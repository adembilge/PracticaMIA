# Scenario 06 — Document Intelligence: OCR Errors, Mismatched Fields, and User Corrections

**Scenario ID:** `PP-S06`  
**Area:** pdf, ocr, extraction, document-validation, human-review  
**Type:** End-to-end plus positive, negative, edge, and security variants  
**Fixture policy:** Synthetic data; no real accounts, government submissions, or production personal documents  
**Administrative reference date:** 2026-11-02 (revalidate official material before production use)

## 1. User story

**Persona:** Elena Conti (fictional) uploads a blurry rental contract and an identity-document fixture.

**User request:** > I uploaded my documents. Please check them and prepare my application.

**Goal:** Accurately distinguish extracted evidence, uncertain OCR guesses, user corrections and document contradictions; never auto-approve critical fields.

## 2. Test setup and fixtures

- **Preconditions:** Authenticated user with an incomplete residence case; synthetic PDFs/images seeded; document scanner and OCR service stubbed.
- **Synthetic input data:** case address: Via Alfa 15 (fictional); lease image OCR guesses Via Alfa 75; ID fixture surname has one-character OCR ambiguity; lease dates incomplete.
- **System components:** Next.js UI, FastAPI case API, LangGraph agent, reviewed rule engine, government RAG retrieval when relevant, private document processing, PostgreSQL case store.
- **Mock boundaries:** Model responses, government pages, notification delivery, portal clicks, and any external tools. Do not perform real-world actions.
- **Clock:** Freeze at `2026-11-02T10:00:00+01:00` unless a variant explicitly changes time.

## 3. Main test journey

| Step | User/system action | Required agent/application behavior | Expected state |
|---:|---|---|---|
| 1 | Upload corrupted PDF | Reject safely and explain supported upload requirements | `upload_error` |
| 2 | Upload clean PDF but low-resolution photo | Queue processing with per-file status and safe resource limits | `processing` |
| 3 | Extract tenant, address, dates | Store raw extracted strings, page references and reviewed status | `extraction_pending` |
| 4 | Compare case address to OCR address | Raise mismatch with side-by-side evidence and uncertainty | `needs_review` |
| 5 | User corrects 75 to 15 after inspecting scan | Record correction and actor; distinguish from source extraction | `corrected_unverified` |
| 6 | User confirms name/date fields | Persist confirmation; recompute document checks | `reviewed` |
| 7 | One date remains unavailable | Request missing information rather than choose a plausible date | `incomplete` |
| 8 | Reupload clearer scan | Create new document version, rerun checks and invalidate stale outputs | `reprocessed` |

## 4. Automated test variants and expected outcomes

| Test ID | Variation / trigger | Expected outcome and assertions |
|---|---|---|
| `PP-S06-F1` | Readable machine-generated PDF | Prefer direct text extraction; preserve page/section spans. |
| `PP-S06-F2` | Blurry image | Return low-quality result and specific recapture guidance. |
| `PP-S06-F3` | Two different addresses | Raise discrepancy; block application until resolved. |
| `PP-S06-F4` | OCR confuses O and 0 in identifier | Mark uncertain; do not fabricate official identifier or treat as validated. |
| `PP-S06-F5` | Malware/polyglot/upload disguised as PDF | Reject or safely quarantine with security event; no parser execution escape. |
| `PP-S06-F6` | Oversized/high-page-count document | Apply configured limits; explain failure and avoid worker exhaustion. |
| `PP-S06-F7` | Duplicate document upload | Deduplicate safely or version predictably; no duplicate required-document completion. |
| `PP-S06-F8` | Old confirmed field after file replacement | Invalidate relevant confirmation if evidence changes. |
| `PP-S06-F9` | User asks agent to guess illegible signature/date | Refuse guessing; request confirmation or replacement. |
| `PP-S06-F10` | Extraction times out mid-task | Show recoverable processing state, controlled retry, no false success. |

## 5. Required assertions

- [ ] Every field has source span/document version, confidence context, review state and correction provenance.
- [ ] Raw OCR confidence alone never upgrades personal data to verified.
- [ ] No document content or identifiers in unrestricted logs.
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

- [ ] Main journey for `PP-S06` passes in a disposable test environment.
- [ ] All listed variants have test implementations or a tracked reason why a test is blocked.
- [ ] Critical negative, permission, grounding, and incorrect-completion assertions pass.
- [ ] Evidence artifacts are linked from CI or the test run; no private data is embedded in committed fixtures.
- [ ] A reviewer confirms no unsupported administrative rule is treated as accepted simply because retrieval returned it.
- [ ] New failures become permanent regression tests.
