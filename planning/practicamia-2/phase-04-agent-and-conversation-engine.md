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
- **38.4** Recheck outdated proposals if case data or sources change. Verify freshness and permissions before committing.
- **38.5** Pause with LangGraph `interrupt()` and resume the same thread after approval. A node can re-execute, so use a separate idempotent step for durable writes after approval. [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- **38.6** Show the official channel and next action. Users handle official sign-in, signing, payment, and submission in that channel. Update status from available evidence.

**Acceptance.** Only the displayed and approved change is applied. Duplicate approval or old proposals cannot cause incorrect writes.

## 39. Manage multiple tasks in one conversation

- **39.1** Identify separate goals in one message, with individual procedure candidates and missing context.
- **39.2** Show the active task. Present the choices and ask where to start when the user gives no preference.
- **39.3** Verify case selection server-side. Clarify references such as “the other application” when several records match.
- **39.4** Reuse confirmed shared facts. Keep task-specific dates, documents, and fields with the relevant case.
- **39.5** Allow switching while a question is pending. Show the relevant work and question when the user returns.
- **39.6** Test cross-case isolation with similar document names, different municipalities, and two pending questions.

**Acceptance.** Users can switch between two tasks and return from the same conversation. Citations, fields, and pending work remain bound to their respective cases.

## 40. Evaluate the agent and close Phase 4

- **40.1** Combine Phase 2 cases with correct Phase 3 authorities and passages. Cover wrong authorities, missing locations, stale sources, corrections, multiple goals, and resumption.
- **40.2** Measure intent, procedure retrieval, evidence, question quality, and authorised tool calls separately.
- **40.3** Use unassisted arrival at the correct next action as the primary outcome. Track correct authorities, supported citations, unnecessary questions, and uncorrected misrouting.
- **40.4** Simulate catalogue outages, model timeouts, duplicate messages, and closing the application during approval.
- **40.5** Measure time to first user-visible event, verified response latency, call counts, and cost per case. Set targets from pilot measurements.
- **40.6** Record how failures relate to intent, query, tool, and source version. Verify that monitoring excludes unnecessary conversation and document contents.
- **40.7** Hand off the message API, events, citations, questions, approvals, and reconnection examples to Phase 5.

**Acceptance.** In a pilot set spanning at least three authorities, the agent finds a competent authority, applicable evidence, and a concrete next step. It clarifies missing or conflicting facts. Users can close and reopen the same task.

## End-to-end closure scenario

The user describes a need without knowing the authority. The agent finds the task and source and asks a question when necessary. After a correction, the agent reassesses affected results, shows the action, competent channel, and supporting passage, then lets the user save the task and resume it after returning.
