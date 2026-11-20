# PracticaMIA 2.0 — Phase 4 · Single specialist agent and conversation engine

**Roadmap tasks 31–40.** The first free-text PracticaMIA agent identifies intent, queries the Phase 3 catalogue, clarifies when necessary, and offers a sourced next action. Users can return to their work and any pending question.

**Proposed foundation.** Use one LangGraph agent on the existing Python backend and PostgreSQL. The initial slice supports procedure discovery, sourced explanations, and next actions. Attach document reading, form preparation, and receipt-based tracking as tools in later phases. Verified procedure coverage controls capability availability.

## 31. Define the agent API and interface contract

The [Task 31 contract proposal](phase-04-agent-api-contract.md) includes offline wire models and synthetic fixtures for requests, events, results, citations and reconnect cursors. The agent endpoint remains gated on the Phase 3 catalogue and review.

- **31.1** Use a `thread_id`, `run_id`, optional `case_id`, and increasing event sequence number. A thread can link to multiple cases.
- **31.2** Define typed requests for sending a message, stopping, retrieving a result, and responding to pending approval. Identify retries by client message ID.
- **31.3** Define user-visible events. Proposed types include `run.started`, `progress.updated`, `question.requested`, `approval.requested`, `answer.completed`, and `run.failed`. Adapt provider and graph events to the application contract.
- **31.4** Support a short explanation, next action where relevant, official channel, citations, and missing information. Carry action copy and the executable operation in separate fields.
- **31.5** Reconnect after the last observed event. The isolated stop operation records a terminal event at the current revision, clears the worker state and fences any result in flight. The isolated browser control displays the server-confirmed outcome and refreshes stale state before another user-initiated stop. Reporting already committed case changes remains part of the later write approval flow.
- **31.6** Send progress events promptly. Show consequential claims about authorities, fees, and dates after verification. [LangGraph streaming](https://docs.langchain.com/oss/python/langgraph/streaming)

**Acceptance.** One API contract supports answers, questions, source cards, approvals, and errors in the frontend.

## 32. Build a single LangGraph graph

The [Milan evidence handoff](../../docs/APPROVED_PASSAGE_SEARCH.md#phase-4-evidence-handoff) exercises the existing approved search and citation checks with a typed Phase 4 consumer. Each lookup checks the authenticated user’s thread, the explicit case link and the case’s current confirmed intake before resolving evidence. The first graph awaits the reviewed catalogue and pilot workflow specified by the [API contract](phase-04-agent-api-contract.md#acceptance-and-dependency-checks).

| Node | Result |
| --- | --- |
| Load context | Authorised thread and case context |
| Identify intent | Intent, procedure candidates, and known facts |
| Find the procedure and evidence | Applicable authorities, procedures, sources, and open questions |
| Choose the next step | Answer, clarification, tool call, or proposal |
| Verify and respond | Sourced response or explicit uncertainty |

- **32.1** Give nodes typed inputs and outputs. Prevent intent nodes from writing directly to durable case state.
- **32.2** Define transitions for direct answers, missing information, and tool calls. Validate tool results before answering.
- **32.3** Check model-proposed routes against procedure scope, authorisation, tool availability, and input completeness on the server.
- **32.4** Define budgets for searches, time, tool calls, and model calls. End repetitive queries with the available result or an explanation of the verification gap.
- **32.5** Implement the first vertical slice. Free text → catalogue → clarification when needed → sourced next action. Preserve the existing response path when adding a tool.

**Acceptance.** One chat supports direct answers and waiting for information. A tool failure produces a recoverable route.

## 33. Persist conversation, case, and resumption state

The [thread ownership service](../../backend/app/agent/threads.py) uses server-issued IDs and accepts links only when the principal owns both the thread and case. Retrying a link leaves one row. Deleting a thread or case removes its links. Migration `20261118_0018` adds the two tables. The [message acceptance service](../../backend/app/agent/run_requests.py) records encrypted messages with their queued run IDs and thread revisions. An identical retry returns the original run and a changed payload conflicts. Thread ownership, active-run uniqueness, and explicit case linking are enforced at acceptance. A new worker can recover the saved message. The [encrypted event journal](../../backend/app/agent/run_events.py) records ordered events and the run status in one transaction. A reconnect can read the remaining user-visible events using its last observed sequence. The journal also supplies the stored terminal answer. The [worker checkpoint service](../../backend/app/agent/checkpoints.py) keeps the latest encrypted state at a persisted event boundary. The checkpoint records the next node and typed references for pending work. A save can commit an event and its checkpoint together, and compares both the checkpoint revision and event watermark to reject stale writes. A worker encountering an event ahead of its checkpoint must reconcile before resuming. The [internal worker](../../backend/app/agent/worker.py) reads this boundary from a fresh transaction and calls one read-only step at a time. A replacement worker skips completed steps. An uncommitted step can be retried after interruption, and a stale worker cannot publish a terminal answer. The [internal scheduler](../../backend/app/agent/worker.py) claims one eligible run through an expiring database lease. It releases the reservation when it commits a step. Following an interruption, another worker can claim the run after expiry and recover its checkpoint. A worker can also return a typed clarification. This atomically writes the question event and its checkpoint, puts the run in `waiting_for_information`, and releases the lease. A new session can replay the question from its last observed sequence. The internal reply service resumes the same owned run after accepting a reply for the pending question and revision. The reply event, cleared pending-question reference and running status commit together. The first resumed step receives the reply from the journal, including after an interrupted attempt. An isolated FastAPI client uses a signed token to discover its active runs, then uses the returned thread and run IDs to replay the question, send a reply and read the final result. The localhost [Chromium acceptance scenario](../../docs/ACCEPTANCE_TESTING.md#acceptance-scenarios) exercises the same path in a fresh browser context and retries the saved reply after a simulated response loss. The acceptance bridge runs a background worker that polls for eligible work and processes bounded batches. The browser submits the reply and reads the result committed by the worker. Each batch stops on an empty queue or when it uses its attempt budget. A lease conflict uses one attempt and the displaced worker cannot commit its result. Hosted scheduling, LangGraph integration, live streaming, retention and public endpoints remain open.

- **33.1** Model messages, checkpoints, and cases. Messages hold conversation, checkpoints hold execution state, and cases hold confirmed facts and pending work. [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- **33.2** Keep the active case, candidates, known and missing fields, sources, pending question, and proposal IDs in agent state. Use authorised references for large files.
- **33.3** Resume from the last consistent point after a closed browser, worker restart, or interrupted model call.
- **33.4** Start with one active run per thread. Detect conflicts with case revisions when separate conversations update the same case.
- **33.5** Minimise sensitive data in checkpoints. Define cleanup for case deletion and retention expiry.
- **33.6** For long conversations, pass relevant recent messages, confirmed facts, and open actions. The worker reloads up to three earlier user messages from completed runs in the same owned thread and exact case scope. An unlinked run sees only unlinked history. It reads the messages as conversation data in accepted order. For a linked case, each worker step also reads a typed snapshot of explicitly user-confirmed intake and open checklist review IDs. The current signed workflow validates the action IDs and invalidates prior acknowledgements when its fingerprint changes. The snapshot carries intake and checklist next actions. Document and package decisions belong to their own workflow services.

**Acceptance.** The user can return to a pending question. Retried requests create no duplicate cases, tasks, or writes.

## 34. Develop intent, procedure, and authority matching

- **34.1** Define the six [typed intent labels](phase-04-agent-api-contract.md#internal-intent-labels) for the worker. A checkpoint can save an intent across resumption.
- **34.2** Extract typed intents, authority and place expressions, procedure candidates, and missing context. The [isolated extraction step](phase-04-agent-api-contract.md#internal-intent-extraction) validates exact name matches against supplied reviewed catalogue records and retains unresolved distinctions.
- **34.3** Match reviewed everyday names and acronym variants in the Phase 3 catalogue. The [scoped Milan search adapter](../../docs/APPROVED_PASSAGE_SEARCH.md#phase-4-evidence-handoff) uses a bounded lexical retry for bilingual address phrases and preserves the distinction between `residenza` and `domicilio`.
- **34.4** Evaluate saved procedure candidates against [confirmed location roles, dates and circumstances](phase-04-agent-api-contract.md#procedure-candidate-applicability). The assignment's required location role determines which case fact establishes the area.
- **34.5** The [isolated outcome step](phase-04-agent-api-contract.md#empty-and-conflicting-procedure-results) explains unresolved candidates, asks a distinguishing question or offers a separately reviewed and applicable official assistance channel.
- **34.6** The [synthetic matching matrix](phase-04-agent-api-contract.md#bilingual-matching-evaluation) tests Italian and English messages, incomplete sentences, spelling mistakes, acronyms and competing authority names.

**Acceptance.** Intent recognition and official procedure selection are independently measurable. Definitive routing depends on a verified authority.

## 35. Implement clarification and user corrections

- **35.1** The [clarification context check](phase-04-agent-api-contract.md#context-before-a-clarification) reuses confirmed case facts and checks the current message and accessible document results before asking.
- **35.2** The [question priority step](phase-04-agent-api-contract.md#prioritizing-clarifications) asks for the field that can narrow or settle a reviewed assignment. It explains why details are needed together when one authority's remaining assignments all require the same missing facts.
- **35.3** The [reply validation step](phase-04-agent-api-contract.md#validating-clarification-replies) checks free text and offered choices against the saved question. It explains the expected answer and keeps the question available for correction.
- **35.4** [Clarification deferrals](phase-04-agent-api-contract.md#deferring-a-question-or-changing-topics) retain the open fields, allow supported work to continue, and let a new topic start after closing the previous run without resolving its question.
- **35.5** [Recheck routing and evidence](phase-04-agent-api-contract.md#reevaluating-a-correction) when a reply supplies a corrected value. Continue to the next needed field or refresh current approved evidence for the revised scope.
- **35.6** [Recover from stale questions](phase-04-agent-api-contract.md#recovering-from-a-stale-question) across browser tabs. Bind each reply to its question ID and revision and reload after a conflict.

**Acceptance.** Users avoid repeating confirmed facts. Corrections update relevant sources and actions.

## 36. Run typed, authorised, and retry-safe tools

| Tool | Initial function |
| --- | --- |
| Find procedure | Procedure, authority, jurisdiction, and channel candidates |
| Find evidence | Reviewed and applicable passages |
| Open source details | Version, official URL, scope, and location |
| Read case context | Authorised facts and pending work |
| Propose case update | Draft field or task change |
| Apply approved update | Commit a write with valid approval and revision |

- **36.1** Define [typed tool inputs and outputs](phase-04-agent-api-contract.md#typed-tool-contracts). Validate catalogue IDs and reject unknown parameters.
- **36.2** [Verify the acting user and ownership](phase-04-agent-api-contract.md#authorizing-tool-calls) server-side. Scope case tools to the case stored with the run.
- **36.3** Define [tool execution conditions](phase-04-agent-api-contract.md#checking-tool-execution-and-approval) for reads, drafts, and approved writes.
- **36.4** [Persist retry receipts](phase-04-agent-api-contract.md#retrying-an-approved-case-write) with the approved update to prevent duplicate writes after a retry or resume.
- **36.5** [Recover from catalogue lookup problems](phase-04-agent-api-contract.md#recovering-from-catalogue-lookup-problems) with bounded retries and actionable unverified results.
- **36.6** Define [document and form extension contracts](phase-04-agent-api-contract.md#document-and-form-extension-tools) and return unavailability until their executors are enabled.

**Acceptance.** Tests cover unauthorised access, invalid calls, and duplicate writes. Visible state reflects the actual operation.

## 37. Implement sourced responses and claim verification

- **37.1** [Link consequential claims to passage IDs](phase-04-agent-api-contract.md#linking-claims-to-evidence) for authorities, channels, mandatory documents, fees, deadlines, conditions, and form versions.
- **37.2** [Revalidate references for freshness and applicability](phase-04-agent-api-contract.md#revalidating-answer-evidence). Check procedure, location, date, and conditions.
- **37.3** [Verify exact passage support for each claim](phase-04-agent-api-contract.md#checking-passage-support-for-claims). A general authority link does not substantiate a date missing from the page.
- **37.4** [Keep supported claims and guide verification of missing information](phase-04-agent-api-contract.md#publishing-answers-with-partial-evidence). Give the known official channel when its evidence applies.
- **37.5** [Preserve information origin](phase-04-agent-api-contract.md#preserving-information-origin) for user documents, official sources, and agent proposals.
- **37.6** [Open exact Phase 3 passages from source cards](phase-04-agent-api-contract.md#opening-exact-source-cards) and explain the original Italian terms in the user's language.

**Acceptance.** Critical claims lead to a valid passage. Evidence from another municipality, withdrawn sources, and old versions cannot appear verified.

## 38. Build proposals, user approval, and safe resumption

- **38.1** [Record case input provenance](phase-04-agent-api-contract.md#recording-case-input-provenance) for user statements, extracted values, and user-confirmed values.
- **38.2** [Preview the exact proposed change](phase-04-agent-api-contract.md#previewing-a-proposed-case-change) with its ID, affected field, existing and proposed values, rationale, and case revision.
- **38.3** [Handle proposal decisions](phase-04-agent-api-contract.md#recording-proposal-decisions). Validate corrections before review and prevent declined proposals from being applied.
- **38.4** [Recheck outdated proposals before committing](phase-04-agent-api-contract.md#rechecking-proposal-freshness). Verify the current case, exact source versions, and permissions.
- **38.5** [Pause with LangGraph and resume the same thread after approval](phase-04-agent-api-contract.md#resuming-a-langgraph-approval). Apply the approved change as a separate idempotent step. [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- **38.6** [Show the verified official channel and next action](phase-04-agent-api-contract.md#showing-the-official-handoff). Users handle official sign-in, signing, payment, and submission in that channel. Determine handoff status from current evidence.

**Acceptance.** Only the displayed and approved change is applied. Duplicate approval or old proposals cannot cause incorrect writes.

## 39. Manage multiple tasks in one conversation

- **39.1** [Identify separate goals in one message](phase-04-agent-api-contract.md#identifying-separate-goals), with individual procedure candidates and missing context.
- **39.2** [Display task choices and the active task](phase-04-agent-api-contract.md#choosing-the-active-task). Ask where to start when the request has no clear preference.
- **39.3** [Verify saved-case selection on the server](phase-04-agent-api-contract.md#verifying-the-selected-case). Clarify references such as “the other application” when several records match.
- **39.4** [Reuse confirmed shared facts](phase-04-agent-api-contract.md#reusing-confirmed-shared-facts). Keep task-specific dates, documents, and fields with the relevant case.
- **39.5** [Switch while a question is pending](phase-04-agent-api-contract.md#switching-between-pending-case-tasks). Show the relevant work and question when the user returns.
- **39.6** [Test cross-case isolation](phase-04-agent-api-contract.md#testing-isolation-between-pending-cases) with similar document names, different municipalities, and two pending questions.

**Acceptance.** Users can switch between two tasks and return from the same conversation. Citations, fields, and pending work remain bound to their respective cases.

## 40. Evaluate the agent and close Phase 4

- **40.1** [Assemble the agent development set](#agent-development-evaluation-set) from Phase 2 scenarios and Phase 3 authority and evidence records. Cover wrong authorities, missing locations, stale sources, corrections, multiple goals, and resumption.
- **40.2** [Measure the agent components separately](#agent-component-measurement) for intent, procedure retrieval, evidence, question quality, and authorised tool calls.
- **40.3** [Use unassisted arrival at the correct next action](#unassisted-next-action-evaluation) as the primary outcome. Track correct authorities, supported citations, unnecessary questions, and uncorrected misrouting.
- **40.4** [Simulate interrupted runs and client recovery](#interruption-and-recovery-scenarios) for catalogue outages, model timeouts, duplicate messages, and closing the application during approval.
- **40.5** [Measure response time, calls and cost per case](#agent-performance-measurement). Set targets from pilot measurements.
- **40.6** [Record failure metadata](#failure-monitoring-metadata) by intent, query type, tool, and source version. Verify that monitoring excludes conversation and document contents.
- **40.7** [Hand off the message API, events, citations, questions, approvals and reconnection examples](phase-04-phase-05-handoff.md) to Phase 5.

**Acceptance.** In a pilot set spanning at least three authorities, the agent finds a competent authority, applicable evidence, and a concrete next step. It clarifies missing or conflicting facts. Users can close and reopen the same task.

### Agent development evaluation set

The [versioned development set](../../evals/fixtures/phase04_agent_development.json) has 13 synthetic scenario families, each with English and Italian inputs. Every family links to the corresponding Phase 2 scenario or rehearsal. The reference map names four bodies across the three procedures and links each assignment to its Phase 3 role or channel locator. The cases cover wrong authorities, missing locations, withdrawn evidence, an obsolete form, a destination correction, multiple goals, unreadable notices, and resumption.

The Milan handoff expectations use the two exact source versions and three passage IDs cited by the [signed first-route catalogue](../../requirements/milan-residence-change/reviewer_approved_signable_catalog_v1.json). Torino banns, postal permit intake and Questura steps use research locators. Their expected responses preserve review gaps and withhold unverified citations or filing destinations. The public evidence from [Torino's office and service pages](https://www.comune.torino.it/amministrazione/ufficio-pubblicazioni-matrimonio-0) and [the permit procedure page](https://www.portaleimmigrazione.it/ITA/nuovaProcedura.html) identifies review targets. The Milan FAQ returned an access error on direct lookup. Its version and passage references come from the [dated owner-review record](../../docs/MILAN_FIRST_ROUTE_OWNER_REVIEW_ACTIVATION_2026_11_08.md) and the signed catalogue.

Read the sequence in one language at a time. Each step supplies an input or a state event and an observable expected outcome. The `facts` entries specify controlled evaluation context, with `null` for a missing fact. Saved case writes follow the existing owner approval flow. The `question_step` reference identifies the question to reopen or answer. For a goal reply, translate `selected_procedure_id` into the exact displayed option when replaying the API. A `source_change` invalidates the named reference before reopening current guidance. Previous events retain their history.

From `backend/`, run `python -m pytest -q tests/test_agent_development_dataset.py` to verify the dataset links, both languages, question transitions, and the Milan outcomes against the signed rule engine with controlled passage availability. The check runs offline. The [Phase 2 collection record](phase-02-user-case-sampling.md#collection-status) records no enrolled cases, and the [Phase 3 closure checklist](phase-03-official-sources-and-catalog.md#phase-3-closure-checklist) still requires review of the broader catalogue. Participant evidence, a reviewed multi-authority pilot set and hidden holdout cases remain open.

### Agent component measurement

From the repository root, with the backend dependencies installed, run `PYTHONPATH=backend python evals/score_phase04_agent.py`. The JSON records the fixture ID and SHA-256 digest, exact expected and observed values for each probe, and a separate pass count and rate for each dimension.

| Dimension | Baseline | Scoring unit |
| --- | ---: | --- |
| Intent | 9/26 | Exact intent label on each bilingual opening, including missed intents |
| Procedure retrieval | 15/26 | Exact set of extracted procedure candidates on the same openings, including openings with no applicable procedure |
| Evidence | 20/20 | Exact set of published passage references on Milan turns after revalidating synthetic source versions, destination scope and claim support |
| Question quality | 14/22 | Exact requested fields on openings that expect clarification, a task choice or guidance without a question |
| Tool authorisation | 9/9 | Exact server preflight decision across run state, owner, case, catalogue scope, capability and approval probes |

Intent and procedure retrieval use the same extractor with a controlled set of aliases. The question probe supplies the expected intent and procedure candidates to test field selection independently of extraction. It checks what the question asks for. Wording and user comprehension remain to be evaluated. The question misses cover the Torino celebration municipality, permit category, appointment date and cropped attachment name in both languages. Procedure candidate misses include Italian Milan requests and requests for Torino banns and permit intake in both languages.

Evidence uses a disposable approved registry with synthetic text linked to the signed Milan passage IDs in the report. The replay exercises missing and changed destinations, withdrawal and an unsupported form claim. Toolkit probes execute the typed parser and server preflight on temporary case and run state. This offline benchmark measures components on development cases. Live source verification, end-to-end dialogue, participant outcomes and the wider reviewed catalogue remain outside this baseline.

### Unassisted next-action evaluation

From the repository root, with the backend dependencies installed, run `PYTHONPATH=backend python evals/score_phase04_next_action.py`. The report identifies the dataset version and SHA-256 and records the expected and observed actions by scenario, language and turn.

The primary outcome is the share of scenario-language runs that reach the expected next action at every checkpoint using only the scripted user inputs. A matching turn requires the specified action, exact question fields or selected task where applicable, and the expected authority and passage set. The script submits a clarification reply only when the correctly scoped question is pending. A reopen uses the same saved question ID and revision. A withdrawal reads the current handoff from the saved answer after revoking the disposable source. Remaining scripted turns count in the denominator even when a required step is missed.

| Measure | Baseline | Counting rule |
| --- | ---: | --- |
| Unassisted next action | 3/26 (11.5%) | Scenario-language runs with every checkpoint correct |
| Correct turns | 11/36 | Matching checkpoints across all scenarios and both languages |
| Correct authority | 4/10 | Required authority turns with the exact verified authority |
| Supported citations | 12/12 emitted, 30 required | Published citations on the exact expected passage list |
| Unnecessary questions | 17/22 emitted | Newly recorded questions asking for one or more fields outside the expected set |
| Uncorrected misrouting | 0/26 | Scenario-language runs ending with an incorrect published channel still in effect |

The runner saw four official-channel turns. Both language variants of the pending-destination case restored the correct question, then missed the verified handoff after the reply. Both variants of the multiple-goal case offered the right initial choice, then missed the follow-up about the selected procedure. Neither opening in the withdrawal scenario reached the initial handoff. A regression test starts from a wording that reaches it and confirms that source withdrawal removes the current channel while retaining the historical answer.

The replay executes the owned worker, saved clarification and event services over a separate in-memory database per run. It uses a limited alias catalogue and a synthetic answer adapter that evaluates signed Milan conditions and sends draft claims through the worker's evidence checks. A result must include the requested action. Generic questions lack the specific redacted-excerpt action, and an unverified response without a filing or correction action misses that checkpoint. These results describe simulated interactions through the internal backend. Participant success, live source verification, model behaviour and browser usability need their own evidence.

### Interruption and recovery scenarios

| Interruption | Observed recovery |
| --- | --- |
| Catalogue unavailable | The corrected-scope lookup retries once in a fresh session. A second failure records `catalogue_unavailable`. A new request in the same conversation reaches verified-response preparation after the synthetic catalogue recovers. |
| Model deadline exceeded | The execution adapter signals `ModelProviderTimeout`. The worker records a retryable `provider_unavailable` failure event with `retry_later`, releases its lease, and clears the finished checkpoint. The owner can send a new request while the failed run remains readable. |
| Message acknowledgement lost | Repeating the same message ID and payload returns the original run before and after completion. Sending a changed body with the same ID conflicts. The worker runs once and writes one terminal answer. |
| App closed during approval | A new mobile Chromium context discovers the same pending proposal and journal. The saved case remains at the original value until the owner reviews and accepts the replacement proposal. The journal then shows a single applied operation and the original run resumes. |

From `backend/`, run `python -m pytest -q tests/test_agent_catalogue_recovery.py tests/test_agent_recovery_http.py tests/test_agent_approval_resume.py`. These tests use signed synthetic JWTs and disposable database state. The model case injects a timeout at the execution boundary. The Chromium checks exercise general retry guidance with stubbed failure events and app closure with the actual isolated FastAPI approval flow and disposable PostgreSQL. Hosted agent scheduling, live model response deadlines and live identity sessions still require separate evidence.

### Agent performance measurement

From the repository root, run `PYTHONPATH=backend python evals/measure_phase04_agent.py --repeat 3` with the backend dependencies installed. It replays the same dataset as Task 40.3 with a monotonic clock. Each measured request starts before the message or clarification reply is sent to the internal service. The first observable state is the returned question, approval, answer or terminal status. A verified sample requires a verified published answer with a revalidated channel. Reopen and source-withdrawal housekeeping are outside the request timings. The baseline uses nearest-rank percentiles and a fresh in-memory database per scenario.

| Metric | Local synthetic baseline |
| --- | ---: |
| First client-readable state, 96 requests | p50 35.9 ms, p95 54.4 ms |
| Verified response, 12 of 96 requests | p50 43.2 ms, p95 54.4 ms |
| Worker steps, 78 case runs | 264 |
| Typed server tool checks, 78 case runs | 132 `read_case_context` checks |
| Paid model calls and spend | 0 calls and USD 0 per case |
| Cases reaching all expected next actions | 9/78, three repeats of the same 26 scenarios |

The offline timing includes worker execution, persisted state and read-side projection. It excludes setup, hosted queue delay, the browser and the network. The invocation counts include worker steps and typed server tool authorisation checks. The deterministic adapter incurs zero paid provider spend. Hosting and database costs require separate measurements.

The Chromium acceptance report also captures two click-to-display times under `agentPerformanceMs`. The first measures a new task until its question appears. The other measures a clarification reply until the reviewed handoff link is visible, including a forced lost acknowledgement and a repeat submission. These single-run observations include polling and browser interaction on the isolated test stack.

Numeric pilot targets remain open. The [pilot guide](../../docs/MILAN_PILOT.md#agent-performance-observations) specifies how to collect participant timing, verified coverage, calls and billed cost on a reviewed build. The synthetic baseline documents the current worker and supports repeat measurements during development.

### Failure monitoring metadata

The isolated backend emits one structured JSON record under `app.agent.diagnostics` at the failure boundary. The schema contains an event name and version, failure code, execution stage, known intent, query type, tool name, and a bounded list of related public registry version IDs. Query type distinguishes corrected message search, procedure-hint lookup and model requests. Unknown or inapplicable dimensions are empty.

| Failure | Metadata source |
| --- | --- |
| Corrected catalogue lookup is rejected, returns no evidence or exhausts its retry | Checkpoint intent, bounded query type, and tool name once the lookup starts |
| A typed case or evidence read is denied | Owned checkpoint and actual tool name |
| Model deadline expires | Checkpoint intent and model request category |
| Publication revalidation changes the verification status, citations, claims or channel | Checkpoint intent and draft citation versions linked to reviewed assignments in the server scope |
| Approval requires a new review | Checkpoint intent, approved update tool and versions from the saved proposal's verified evidence dependencies |

Source version IDs describe the evidence considered at the failure boundary. Terminal failure and publication records are emitted after the journal transaction commits. Read denials and invalid or empty lookups record the attempt at the read boundary. Exact approval retries replay the existing result without emitting another diagnostic.

The schema has no free-text or private identifier fields. Prompt, query, reply, OCR, document, proposal and exception details stay out of this logger. Tests capture and inspect the exact JSON, including a synthetic uploaded PDF and its extracted date, a model exception with private test values, failed source revalidation with a forged reference, and a revoked approval dependency. These tests exercise the isolated worker and signed routes. Collector configuration, retention and verification of hosted log pipelines remain release work.

### Bilingual intent follow-up

The unchanged Task 40.1 messages and expected answers were replayed after extending the extractor's English and Italian filing and limit questions. The evaluation also added `indirizzo all’anagrafe` as a synthetic procedure alias using the civil-registration example in [Phase 2](phase-02-administrative-domains.md).

| Measurement | Phase 4 baseline | New cues and original aliases | New cues and updated synthetic aliases |
| --- | ---: | ---: | ---: |
| Exact opening intent | 9/26 | 15/26 | 16/26 |
| Exact procedure candidate set | 15/26 | 15/26 | 17/26 |

With the updated synthetic aliases, the unassisted replay passed 5/26 case-language runs and 13/36 checkpoints. The Italian wrong-authority scenario reached the verified Milan route, and the Italian missing-destination scenario asked for the municipality. The former results were 3/26 and 11/36. There were five official-channel turns and no observed misrouting in these development examples. The Italian opening that merely names an address in Milan still needs a procedure candidate, and the notice and saved-case continuation gaps remain.

Run `PYTHONPATH=backend python evals/score_phase04_agent.py` and `PYTHONPATH=backend python evals/score_phase04_next_action.py` from the repository root. These comparisons use the development set. The test verifies that a pending or absent alias cannot identify the procedure and that a generic domicile phrase leaves it unresolved. Broader catalogue review and participant evaluation remain open.

### Pending destination on a reopened case

The English and Italian flows now accept an explicit destination sentence as an answer to the recorded destination question. The worker resolves the municipality against the supplied reviewed catalogue, drops previous evidence, and binds the new routing value to the reply event. Ambiguous names and questions stay unresolved.

The isolated worker searches the currently approved Milan procedure only when the active saved intake independently satisfies the case gate. A draft intake gets a specific confirmation action. An archived case stops at an unverified result. Neither path changes saved intake. The confirmed variant resumes the same run at the evidence verification step.

From `backend/`, run `python -m pytest -q tests/test_agent_routing_corrections.py`. The signed HTTP examples restore the question from the journal and submit the original bilingual sentences. They exercise draft, confirmed and archived intake. The development benchmark still passes 5/26 cases and 13/36 checkpoints. Its reopened-destination scenario expects verified guidance after the reply without a saved intake confirmation, so it remains a miss under the case gate.

### Unreadable notice details

When a user describes an unreadable appointment date or attachment name in a notice, the worker asks for the one relevant line in English or Italian. It asks the user to remove personal details and to check with the issuing office if the line stays unreadable. The signed HTTP replay restores the question after reconnection. Text and deferred replies lead to an insufficient-evidence result with the field still open. The result gives a next step without echoing the reply.

The unchanged synthetic development set now passes 9/26 scenario-language runs and 17/36 checkpoints, up from 5/26 and 13/36. The four gains come from the two unreadable-notice scenarios in both languages. Exact opening intent increased from 16/26 to 20/26 and exact question fields increased from 14/22 to 18/22. Procedure candidates scored 17/26, approved evidence scored 20/20 and tool authorisation scored 9/9. The appointment scenario still requires a reviewed procedure for any verified routing.

Run `python -m pytest -q tests/test_agent_notice_clarification.py` from `backend/` for the signed question and reply checks. The two development benchmark commands are listed in the bilingual intent follow-up above.

### Saved Milan filing and current form checks

The worker recognises bilingual requests for the filing step of a linked saved case. It also recognises a move-and-address-update statement paired with a filing question when the named municipality resolves to Milan. A confirmed active case in the first reviewed scenario can proceed to evidence lookup. The worker checks the intake again before publication, and the channel still requires applicable reviewed evidence. An archived case or a withdrawn intake confirmation during retrieval keeps the result unverified. When a source is withdrawn after publication, the current handoff is withheld and the historical answer stays in the journal.

A question that compares an old ANPR guide's upload limit with the current form produces `check_current_form`. The user can check the current form or ask the registry office for confirmation. The answer leaves the number unresolved and includes no citation or filing link.

The replay now persists complete initial profiles as confirmed intake in its disposable database. The fixture leaves incomplete profiles as drafts. Running the updated replay with the previous worker still gives 9/26 scenario-language runs and 17/36 checkpoints. With the new worker, the same dataset and scoring rules give 14/26 and 24/36. The five newly passing runs are the Italian Milan filing request, both source-withdrawal runs and both old-guide upload-limit runs. The evaluator counted zero uncorrected misroutes. This comparison covers synthetic cases through the isolated worker. The resumed case that still needs a saved intake confirmation and routes without reviewed catalogue support remain open.

Run `python -m pytest -q tests/test_agent_intent_extraction.py tests/test_agent_next_action_evaluation.py` from `backend/` for the bounded phrasing, stale case, withdrawal and old-guide regressions.

### Destination correction in a new message

A linked Milan case accepts explicit destination corrections in English and Italian. The worker resolves the named destination using the supplied reviewed municipality names. A second sentence identifying the previous municipality provides no destination candidate. An unresolved or unsupported destination produces `reassess_destination`. The result has no official channel or citations.

The accepted correction supersedes earlier live handoffs for the same case in that conversation immediately. Earlier answers and their citations remain in the historical journal. Subsequent requests in the same conversation carry the correction's revision and timestamp in their encrypted payload. The saved intake can support a fresh reviewed handoff after the owner confirms the case details again. The message itself does not write saved intake.

The unchanged synthetic development set passed 16/26 scenario-language runs and 26/36 checkpoints, up from 14/26 and 24/36. Both gains come from the Milan-to-Torino destination correction. Torino remains outside the reviewed route. The run confirms that the old Milan channel was withheld and that the newer result explicitly directs the user to reassess the destination.

Run `python -m pytest -q tests/test_agent_source_cards.py tests/test_agent_next_action_evaluation.py` from `backend/` to reproduce the signed handoff and offline replay checks.

### Clarifying unresolved filing context

For a recognised residence-permit renewal without a reviewed route, the worker asks what type of permit the applicant is renewing. When the user reports a postal renewal notice and asks about delivering it at the Questura instead, the worker recommends confirming the filing channel with the issuing office. That response carries no official link or citation.

The marriage-banns clarification keeps registered residence and the ceremony municipality distinct. A clear stated municipality can inform the next question while the route remains unverified. If the user selects banns from a request with multiple tasks and there is no compatible saved case, the next question asks for both municipal roles. The selected task survives reload and reply. The worker preserves the original case link and leaves filing instructions unverified.

The unchanged synthetic dataset and scoring criteria passed 24/26 scenario-language runs and 34/36 checkpoints, up from 16/26 and 26/36. The evaluator reads a follow-up question's selected task from the saved question and encrypted goal state. It observed no uncorrected misroutes and eight verified-channel turns. The remaining two runs are the two languages of the reopened destination scenario and need a separate saved intake confirmation.

Run `python -m pytest -q tests/test_agent_filing_clarification.py tests/test_agent_case_selection.py tests/test_agent_next_action_evaluation.py` from `backend/` to reproduce the clarification, signed reconnect and replay checks.

## End-to-end closure scenario

The user describes a need without knowing the authority. The agent finds the task and source and asks a question when necessary. After a correction, the agent reassesses affected results, shows the action, competent channel, and supporting passage, then lets the user save the task and resume it after returning.
