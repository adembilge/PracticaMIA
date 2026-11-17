# PracticaMIA 2.0 — Phase 4 · Single specialist agent and conversation engine

**Roadmap tasks 31–40.** The first free-text PracticaMIA agent identifies intent, queries the Phase 3 catalogue, clarifies when necessary, and offers a sourced next action. Users can return to their work and any pending question.

**Proposed foundation.** Use one LangGraph agent on the existing Python backend and PostgreSQL. The initial slice supports procedure discovery, sourced explanations, and next actions. Attach document reading, form preparation, and receipt-based tracking as tools in later phases. Verified procedure coverage controls capability availability.

## 31. Define the agent API and interface contract

The [Task 31 contract proposal](phase-04-agent-api-contract.md) describes the request, event, result, retry, and trust boundaries for review. It does not activate an agent endpoint or satisfy the Phase 3 catalogue dependency.

- **31.1** Use a `thread_id`, `run_id`, optional `case_id`, and increasing event sequence number. A thread can link to multiple cases.
- **31.2** Define typed requests for sending a message, stopping, retrieving a result, and responding to pending approval. Identify retries by client message ID.
- **31.3** Define user-visible events. Proposed types include `run.started`, `progress.updated`, `question.requested`, `approval.requested`, `answer.completed`, and `run.failed`. Adapt provider and graph events to the application contract.
- **31.4** Support a short explanation, next action where relevant, official channel, citations, and missing information. Carry action copy and the executable operation in separate fields.
- **31.5** Reconnect after the last observed event. When a user stops a run, report the real status of ongoing work and earlier committed changes.
- **31.6** Send progress events promptly. Show consequential claims about authorities, fees, and dates after verification. [LangGraph streaming](https://docs.langchain.com/oss/python/langgraph/streaming)

**Acceptance.** One API contract supports answers, questions, source cards, approvals, and errors in the frontend.

## 32. Build a single LangGraph graph

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

- **33.1** Model messages, checkpoints, and cases. Messages hold conversation, checkpoints hold execution state, and cases hold confirmed facts and pending work. [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- **33.2** Keep the active case, candidates, known and missing fields, sources, pending question, and proposal IDs in agent state. Use authorised references for large files.
- **33.3** Resume from the last consistent point after a closed browser, worker restart, or interrupted model call.
- **33.4** Start with one active run per thread. Detect conflicts with case revisions when separate conversations update the same case.
- **33.5** Minimise sensitive data in checkpoints. Define cleanup for case deletion and retention expiry.
- **33.6** For long conversations, pass relevant recent messages, confirmed facts, and open actions. Conversation summaries cannot overwrite case records.

**Acceptance.** The user can return to a pending question. Retried requests create no duplicate cases, tasks, or writes.

## 34. Develop intent, procedure, and authority matching

- **34.1** Define intents for requesting information, finding a procedure, explaining a notice, understanding a form field, resuming a case, and planning several tasks.
- **34.2** Extract typed intents, authority and place expressions, procedure candidates, and missing context. Verify identified records in the catalogue.
- **34.3** Use Phase 3 search to match everyday expressions, Italian terms, and acronyms. Test context-sensitive terms such as residenza and domicilio.
- **34.4** Represent how location, date, and circumstance change the candidates. Avoid assuming the user's physical location is the procedure's jurisdiction.
- **34.5** When results are empty or conflicting, explain candidates, ask a distinguishing question, or route to a verified contact as appropriate.
- **34.6** Test Italian, English, incomplete sentences, spelling mistakes, acronyms, and multiple authority names.

**Acceptance.** Intent recognition and official procedure selection are independently measurable. Definitive routing depends on a verified authority.

## 35. Implement clarification and user corrections

- **35.1** Check the message, confirmed case data, and accessible document results before asking a question.
- **35.2** Prioritise information that changes the outcome. Prefer one distinguishing question when possible and explain why grouped fields are needed.
- **35.3** Record the question ID, expected answer shape, and affected field. Accept free text and options. Explain what information is needed after an invalid answer.
- **35.4** Define behaviour for unknown answers, skipping for now, and topic changes. Complete available work and retain open uncertainty.
- **35.5** Reevaluate affected candidates, evidence, and next action when a correction arrives.
- **35.6** Guard against silent changes from old questions or mismatched question IDs across browser tabs.

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

- **36.1** Define typed inputs and outputs. Validate catalogue IDs and reject unknown parameters.
- **36.2** Verify the acting user and ownership server-side. Model output does not confer access.
- **36.3** Define execution conditions for reads and writes. Check required approval on the server.
- **36.4** Prevent duplicate writes during retries, network failures, and resume with idempotency keys and case revisions.
- **36.5** Provide recovery for transient catalogue errors, no verified result, and invalid input.
- **36.6** Define extension contracts for document and form tools. Unavailable capabilities cannot appear as completed work.

**Acceptance.** Tests cover unauthorised access, invalid calls, and duplicate writes. Visible state reflects the actual operation.

## 37. Implement sourced responses and claim verification

- **37.1** Link authorities, channels, mandatory documents, fees, deadlines, conditions, and form versions to evidence IDs.
- **37.2** Accept references retrieved in the current run or revalidated for freshness. Check procedure, location, date, and conditions.
- **37.3** Verify that the passage supports the claim. A general authority link does not substantiate a date missing from the page.
- **37.4** Remove or narrow unverifiable claims. Give the known official channel and the path to verify missing information.
- **37.5** Preserve whether information comes from a user document, an official source, or an agent proposal.
- **37.6** Link source cards to exact Phase 3 passages. Preserve needed Italian terms and explain them in the user's language.

**Acceptance.** Critical claims lead to a valid passage. Evidence from another municipality, withdrawn sources, and old versions cannot appear verified.

## 38. Build proposals, user approval, and safe resumption

- **38.1** Record user statements, extracted values, and confirmed values with their origin.
- **38.2** Show proposal ID, affected field, existing and proposed values, rationale, and case revision.
- **38.3** Implement accept, correct, reject, and cancel. Revalidate corrected values when needed and keep rejected values from being applied.
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
