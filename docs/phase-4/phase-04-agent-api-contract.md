# Phase 4.31 — proposed agent API and interface contract

**Status:** proposed contract with offline schemas and synthetic tests. Active run discovery, run reads, event replay, clarification replies, proposal decisions, and stop requests have isolated authenticated HTTP coverage. Hosted routes, live streaming, case-write integration, and production capability remain pending. The persistence and worker evidence is recorded below. The Phase 3 catalogue and reviewed multi-authority pilot set are not ready for an agent integration. The existing Milan assistant and synthetic preparation chat remain separate.

## Scope and trust boundary

The backend owns thread and run state, authorises every case reference against the authenticated principal, and validates evidence and operations before returning them as verified. A model may suggest an intent, question, or action; it cannot approve a source, select an unsupported jurisdiction as fact, commit a case change, or report official submission. The frontend renders typed server events and never treats a progress message as a completed action.

The first implementation slice may answer from currently approved passages and ask for missing context. Case writes need the later proposal and approval contract in task 38. Document tools remain unavailable until their release gates pass. Phase 3 must supply a typed catalogue response with procedure, authority role, service area, channel, source version, passage, and applicability result before sourced multi-authority answers can be enabled.

## Internal intent labels

Task 34.1 defines one optional typed intent in the encrypted worker checkpoint. The label describes what the user wants. Procedure candidates and evidence remain separate, and a label grants no authority to read a case, interpret a private document, or execute an operation.

| Label | User goal | Synthetic example |
| --- | --- | --- |
| `request_information` | Understand a rule, requirement or term | “What does proof of residence mean?” |
| `find_procedure` | Find the procedure for a single administrative goal | “Come comunico il mio cambio di residenza?” |
| `explain_notice` | Understand a specific notice or communication | “What does this letter from the municipality mean?” |
| `explain_form_field` | Understand the meaning or expected input of a form field | “Cosa significa ‘titolo di occupazione’ in questo modulo?” |
| `resume_case` | Return to previously saved case work | “Can we pick up my saved address change?” |
| `plan_multiple_tasks` | Plan distinct administrative goals | “Devo cambiare residenza e aggiornare la posizione TARI. Da dove inizio?” |

A null intent means no label has been recorded. Older checkpoints can still be loaded. This field is internal to the worker; public requests and responses use the existing contract.

## Internal intent extraction

Task 34.2 adds an [isolated worker step](../../backend/app/agent/intent_extraction.py) using conservative English and Italian cues and exact expressions in the accepted message. The caller supplies currently reviewed authority, place and procedure names. The existing Phase 3 name resolver checks matching records and preserves competing identities. Pending names and names without evidence are excluded. A city appearing only inside a longer authority name supplies no independent location expression.

The step keeps matched expressions and catalogue candidates in memory. It commits the intent, bounded procedure IDs and missing field labels to the encrypted checkpoint through the normal worker boundary. The location gap describes what the message resolved. A later step can apply confirmed case facts after checking the location's role and scope. Resuming a case requires the worker's authorized case context. Exact catalogue identity gives no basis to infer an authority's competence, which location role applies, or whether a procedure is available to the user.

Task 34.3 recognises compact, dotted and letter-spaced forms of reviewed acronyms in messages. The existing Phase 3 resolver preserves any confirmation requirement on the matching identity. The [Milan evidence adapter](../../docs/APPROVED_PASSAGE_SEARCH.md#phase-4-evidence-handoff) also recognises a narrow set of English and Italian address-change phrases as lexical search hints.

The Phase 4 follow-up recognises additional filing questions and requests for limits in English and Italian. A filing cue without a reviewed procedure match keeps the procedure open for clarification. The offline catalogue includes the explicit Italian phrase `indirizzo all’anagrafe` from the [synthetic Phase 2 examples](../research/phase-02-03/phase-02-administrative-domains.md). [Replay results](phase-04-agent-and-conversation-engine.md#bilingual-intent-follow-up) show the effect of the cue change and the fixture alias separately.

Bounded references to the filing step of a saved case can reuse the linked case's confirmed intake for the first Milan route. A move-and-address-update statement paired with a filing question can do the same when the named municipality matches a reviewed Milan name. The checkpoint records when lookup relied on this confirmed case scope. The worker rechecks the owned active intake before publishing any evidence from that path.

Run `python -m pytest -q tests/test_agent_intent_extraction.py tests/test_knowledge_search.py` from `backend/` for synthetic bilingual extraction, saved-worker-boundary coverage and search parity.

## Procedure candidate applicability

Task 34.4 evaluates each procedure ID from the worker checkpoint with the [Phase 3 service-area resolver](../../backend/app/knowledge/service_areas.py). The caller supplies confirmed territorial IDs keyed by their procedural role, confirmed dates keyed by their case field, confirmed circumstances and the set of currently trusted passage IDs. An assignment for a destination uses that destination's confirmed territorial ID. Presence, browser location and office addresses provide no destination fact.

The reviewed assignment can require an explicitly named case date, one or both inclusive calendar bounds and typed circumstance values, such as a housing basis. A configured open bound must reflect the reviewed assignment. Cases with unresolved applicability dates and assignments awaiting review stay outside trusted routing. An assignment that conflicts with known context drops out. Missing information for a still-plausible assignment keeps authority selection pending, with the needed location role, date field or circumstance field in the result.

The [synthetic tests](../../backend/tests/test_agent_catalogue_applicability.py) exercise date boundaries, alternative circumstances, territorial roles and withdrawn evidence. Populating these inputs from the complete reviewed catalogue and user-facing integration remain open.

## Empty and conflicting procedure results

Task 34.5 adds an [internal worker step](../../backend/app/agent/candidate_resolution.py) that uses current applicability evidence and confirmed case facts when choosing a response. It asks a single question in the message language when the goal, procedure or a supported case detail can narrow the outcome. Questions about procedure identity can mention reviewed candidate names and accept a free-text answer. A confirmed location used for the assignment takes precedence over a missing location expression in the message. Explicit requests for several independent procedures preserve those procedures.

A remaining conflict produces `conflicting_evidence`. An empty or incomplete result produces `insufficient_evidence`. Either can offer a public assistance page for one identified procedure if exactly one separately reviewed assistance assignment applies to the confirmed case. The server supplies current registry citations and approval state. The assignment and citation must agree on the procedure, location and exact passage. The page describes where to ask for help. Competence and filing remain unresolved.

The worker persists the question with its encrypted checkpoint. If it cannot interpret a usable value, it leaves the unresolved fields open. A usable correction can lead to a different question or refresh the evidence. The [worker and resolver fixtures](../../backend/tests/test_agent_candidate_resolution.py) use fictional records and cover localized questions, authority collisions, invalid contact scopes and encrypted resumption. Integration with the full reviewed catalogue and a hosted user-facing route remains open.

For a question comparing an old ANPR guide's upload limit with the current form, the result can carry the `check_current_form` next action. The contract restricts this action to an insufficient-evidence result without citations or an official channel.

The resolver asks about missing permit categories and marriage-banns municipality roles when the reviewed catalogue cannot resolve a route. It can return `verify_filing_channel` for conflicting user-reported filing instructions or after gathering context for an unresolved route. That action requires an insufficient-evidence result without citations or an official channel.

## Bilingual matching evaluation

The [Task 34.6 regression matrix](../../backend/tests/test_agent_matching_matrix.py) checks intent and saved procedure candidates independently from authority applicability and clarification outcomes. It uses paired English and Italian messages with complete wording, fragments, misspelled procedures or places, and multiple authority names. Compact, dotted and letter-spaced acronyms preserve the same identity candidate and confirmation requirement. The fixtures exercise a confirmed service area, overlapping assignments and withdrawn evidence.

Message extraction records a gap when an exact procedure or location expression is missing. The outcome step can then ask a targeted question. Standalone catalogue lookup may suggest a one-edit spelling variant for confirmation. These checks run against synthetic catalogue records in Backend CI. Run `python -m pytest -q tests/test_agent_matching_matrix.py` from `backend/`.

## Context before a clarification

Task 35.1 reuses the linked, owned Milan residence-change case's confirmed destination, move-in date and housing arrangement when an assignment needs them. Explicit English or Italian statements in the current message can turn a request for missing information into a request for confirmation. The worker holds a disputed field out of applicability checks when the message or reviewed document evidence conflicts with the saved value.

During the question step, the worker can read encrypted review metadata through the existing private-vault release settings. The read requires an owned case link, current consent, completed scan and unexpired housing document, plus the subject and file allowlists in fixture mode. The question step receives only the review status of supported fields. A document-only suggestion or review can guide a confirmation question. The saved case stays under the existing confirmation workflow, and question events contain no document values or identifiers.

The [synthetic worker tests](../../backend/tests/test_agent_clarification_context.py) verify saved-fact reuse, localized message confirmation, conflict handling, and fallback when document access or review metadata is unavailable. The hosted agent and live vault use still depend on their release gates.

## Prioritizing clarifications

Task 35.2 compares the remaining requirements of reviewed assignments that survived the case and evidence checks. With a known procedure, the [worker](../../backend/app/agent/clarification_priority.py) first looks for a field whose allowed values differ across candidate authorities. It treats alternate assignments to the same authority as alternatives and compares the union of their territorial, date or circumstance conditions for that field. It next prefers a field that could settle an assignment on its own. A relevant conflict or confirmation hint breaks a tie.

The worker can ask for several details in one English or Italian prompt when only one authority remains possible and every remaining assignment for it needs the same missing fields together. The prompt explains the shared purpose and the event lists each affected field. A conflict between two fully applicable assignments can already be explained, even if another assignment still has gaps.

The [synthetic resolution tests](../../backend/tests/test_agent_candidate_resolution.py) exercise grouped prompts and replay, alternative date ranges, withdrawn evidence, contextual questions and overlapping authority coverage.

## Validating clarification replies

Task 35.3 records the question ID, affected fields, answer shape and optional answer format and guidance in the encrypted question event. Older events can be read without the optional fields. A single housing question can offer choices. A single question asking for a new move-in or filing date accepts a valid calendar date in ISO or day-first numeric form within the case date range of 1900 to 2100. Grouped questions and contextual confirmations continue to accept bounded free text.

The server checks the submitted text against the owned, current question before writing an answer event. A reply that fails the question's validation returns `422 invalid_reply` with the recorded guidance or a default for the expected answer shape. The existing question and run revision stay available for a corrected reply. The error does not include the rejected input. A valid reply is recorded as text, with surrounding whitespace removed.

The [isolated HTTP tests](../../backend/tests/test_agent_reconnect_http.py) cover invalid dates, invalid options, private guidance, correction and retry. The isolated Chromium harness renders both input shapes and checks that a user can correct a rejected date and resume the run.

An unreadable notice question uses the optional `redacted_excerpt` format with bounded free text and one affected field, either `appointment_date` or `attachment_name`. The question and its localized guidance request one relevant line with personal details removed. The worker can advise checking the original or the issuing office after a reply. The requested detail remains unverified and the completed result omits the excerpt.

## Deferring a question or changing topics

Task 35.4 accepts `unknown`, `skip` and `change_topic` dispositions without a case value. The isolated client exposes all three controls. The server also recognizes exact short English and Italian phrases such as “I don’t know” and “Non lo so” when the text is not one of the saved options. Each accepted choice uses the same owned question, revision and retry boundary. Previous answer events without a disposition default to `answer`.

After an unknown or skipped reply, the resolver continues with confirmed facts, retains the unanswered fields and can still give an independently applicable official assistance channel. It leaves the skipped information open in the result. The worker ends a changed-topic run with the affected fields and an instruction to send a new message. The new message is submitted as a separate turn on the same thread. The worker limits its conversation history to recent owned messages since the recorded topic change and still checks the exact case scope. Current case facts change only through their own confirmed workflow.

Synthetic tests cover the authenticated reply boundary, scoped history, continued assistance and a topic change from the isolated Chromium interface.

## Reevaluating a correction

Task 35.5 reads the reply with its recorded question. Only the fields requested by that question can supply a corrected routing value. Procedure and municipality names require a unique reviewed catalogue match. Date and housing replies use bounded formats; grouped replies put one labeled detail on each line. Unrecognized and contradictory values leave the affected field open.

The worker stores validated values for the current run in its encrypted checkpoint. It clears previous evidence, checks the revised candidates against reviewed assignments and can ask for a remaining detail. A replacement procedure starts with its own scope. Once the revised routing is supported, the worker searches for fresh approved evidence through the owned-case adapter. The adapter covers the signed Milan route. A scope mismatch or the absence of current evidence returns an insufficient-evidence result. Updating saved intake still requires the existing confirmation workflow.

The [correction tests](../../backend/tests/test_agent_routing_corrections.py) use synthetic assignments and source snapshots to check a worker restart, a fresh source version, an unavailable version, and the handling of old scope.

A new owned request for a linked Milan case can also carry an explicit English or Italian destination correction. The server records its revision and time inside the encrypted request and carries them forward for that conversation and case. Earlier request payloads also remain readable. The current handoff for an earlier answer resolves to `verification_required` once the correction is accepted. Pending or unsupported routing returns `reassess_destination` with insufficient evidence and no citations or channel. A new verified handoff still requires current supported evidence and an intake confirmation after the correction.

When a destination reply leaves saved intake unconfirmed, the result carries `confirm_saved_intake` and the missing field `intake_confirmation`. The same action applies when the owner asks for the filing step on an explicitly linked saved case whose workflow awaits intake confirmation. The snapshot derives the case link from the run's owned, active binding. Confirmation uses the existing case intake endpoint and the owner can then start a fresh filing request on that case. The agent's conversational reply writes no intake facts.

## Recovering from a stale question

Task 35.6 binds a reply to the question ID and run revision displayed in its tab. Under the existing owned-run lock, a stale revision or mismatched question ID returns `409 stale_question` without recording an event, changing the checkpoint or resuming the worker. An exact retry of an accepted reply can still retrieve its stored event as the run moves forward.

On a reply conflict, the isolated browser client explains the rejection, discards the stale draft and retry key, and reloads the same run. Any new question requires a fresh answer. If the reload fails, the stale controls stay hidden and the user can retry the status read. The synthetic HTTP and Chromium tests verify that a replacement question remains pending until an explicit fresh reply is submitted.

## Typed tool contracts

Task 36.1 defines six internal tool calls and results in [the tool contract](../../backend/app/agent/tool_contract.py). The `tool` discriminator selects a schema. Unknown tools and extra fields are rejected, including extra fields in catalogue scopes and case changes. The parser checks location IDs and exact procedure/location pairs against a server-supplied catalogue. Formatted passage IDs identify an exact version and passage. The evidence service still checks current approval and applicability when resolving one.

| Tool | Typed input | Typed result |
| --- | --- | --- |
| `find_procedure` | Name query, language and optional catalogue location | Candidate procedure/location pairs, authority IDs and evidenced channels |
| `find_evidence` | Case ID, procedure/location pair, search terms and bounded limit | Status and applicable passages with citations, or missing information |
| `open_source_details` | Case ID, procedure/location pair and exact citation ID | Status and at most one passage with source version, official URL, scope and section |
| `read_case_context` | Case ID | Confirmed intake, next action and outstanding checklist IDs |
| `propose_case_update` | Case ID, expected revision, one typed fact or checklist change, and rationale | The proposal for user review |
| `apply_approved_update` | Case and proposal IDs, expected revision and client operation ID | Committed operation ID and new revision when an execution service applies the change |

The existing internal Milan evidence reader uses the evidence and source detail models with its owned-case and approved-source checks. Procedure discovery, case context and update schemas define payloads for later tool integration. Parsing an update leaves the case untouched. Acting identity, ownership and actual execution remain server responsibilities.

Run `python -m pytest -q tests/test_agent_tool_contract.py tests/test_knowledge_search.py` from `backend/` to exercise all six schema pairs, invalid catalogue IDs and parameters, and approved-source lookup and withdrawal in the synthetic database.

## Authorizing tool calls

Task 36.2 checks tool ownership against the persisted run in the caller's database transaction. The acting principal comes from the validated API token or the internal worker's persisted lease. The request body can name a case. The server verifies that the run belongs to the principal's thread and that its stored case is still linked and owned by that same principal. Every case-scoped call must name the exact case recorded for the run. A procedure discovery call can use an owned run without a case.

The [ownership guard](../../backend/app/agent/tool_access.py) checks the six typed call variants. The worker uses it when loading case context and refreshing evidence. The [typed evidence reader](../../backend/app/agent/catalogue_evidence.py) uses it for search and exact source details before applying existing approved-source checks. An unavailable run or case produces the same access denial. Ownership permits only moving to the operation's own checks. Approval, execution and revision checks for future writes have their own steps.

The [synthetic authorization tests](../../backend/tests/test_agent_tool_access.py) cover signed-token identity, missing and invalid tokens, case substitution, wrong threads, unlinked runs and deleted or no longer owned cases. A probe mounted only in the test application verifies that denied evidence calls do not reach the lookup.

## Checking tool execution and approval

Task 36.3 checks the owned run before any tool operation. Procedure discovery, evidence search, source details, case context and draft proposals require a `running` run. Evidence and case readers also enforce their existing source and case checks. Drafting a proposal makes no case change.

An `apply_approved_update` call requires a run paused at the matching `approval.requested` checkpoint. The [server gate](../../backend/app/agent/tool_execution.py) locks the owned run, reads the exact proposal from its encrypted event and checks the case, proposal ID, revision and expiration. A server-provided reader must find an explicit accept decision recorded for the same owner, thread, run, case and proposal event. It must also read the current case revision under a lock in the same transaction. The gate returns the persisted proposal for the eventual writer. Missing readers or decisions, rejected or corrected decisions, and stale revisions fail closed.

The [synthetic policy tests](../../backend/tests/test_agent_tool_execution.py) use real encrypted proposals and fixture approval records. The product currently has no approval reader or writer connected. Task 38 covers recording user decisions and safely resuming the workflow.

## Retrying an approved case write

Task 36.4 locks the owned case, then its run, in a single database transaction. The [write boundary](../../backend/app/agent/tool_writes.py) verifies the current approval before executing a new update. The writer applies the stored proposal and advances the canonical case revision by one using the same database session. The writer's change and the receipt commit together. An interruption after a database flush rolls both back.

On retry, the owner receives the original committed operation ID and resulting revision for the same run, client operation ID, case, proposal and expected revision. The receipt remains available after the approval state advances. Reusing the key for a different request or using a new key for a consumed proposal or case revision conflicts. Database uniqueness on the run and key, run and proposal, and case and expected revision protects these rules. Receipts store identifiers and revisions and follow their run or case on deletion.

The [retry tests](../../backend/tests/test_agent_tool_writes.py) use synthetic case writers and the real proposal journal. They exercise rollback and resume, and CI runs separate PostgreSQL tests for simultaneous calls using the same key or the same case revision. Migration `20261119_0023` adds the receipt table. The approval reader, canonical case revision integration and case writer are part of the later approval workflow.

## Recovering from catalogue lookup problems

Task 36.5 covers the worker's approved-evidence lookup after a scope correction. A recognized temporary storage error rolls back the read session. The worker retries once in a separate session and checks ownership and source approval again. If the second read also fails, the worker commits a `run.failed` event with `catalogue_unavailable`, `retryable: true`, and `retry_later` when the journal is writable. The run releases its checkpoint and lets the owner send a new request in the same thread. The isolated reconnect view displays the retry message from that event.

An empty or out-of-scope result preserves the unverified outcome and asks the user to review the case details. Missing information from the evidence tool accompanies that outcome. An invalid search gets a localized instruction to rephrase it within the query limits. Both results carry no citations. Access denials and unexpected database errors retain their existing handling.

The [recovery tests](../../backend/tests/test_agent_catalogue_recovery.py) exercise transient recovery in a fresh session, exhausted retries, signed event replay, a new request after failure, empty results and English and Italian validation guidance.

## Document and form extension tools

Task 36.6 adds three case-scoped requests to the typed tool boundary. The requests carry references. Document access and form preparation remain on their own release paths.

| Tool | Request | Prerequisites for a future executor |
| --- | --- | --- |
| `read_document_evidence` | Case and document IDs, and a bounded set of distinct field IDs | The case owns the document and the document passes consent, scan, retention and evidence review checks. Return selected field references and provenance. |
| `find_applicable_form` | Case ID and a known procedure/location pair | The form is applicable to the case and its current official version is supported by approved evidence. |
| `prepare_form_draft` | Case ID, exact form and mapping versions, and expected case revision | The versions and validated case inputs match the reviewed mapping and required user approvals. The output remains a private draft. |

The current server verifies the owner and running state before returning a `capability_disabled` error with a typed `unavailable` result. The result schema accepts identifiers for the tool and its unavailable state. It rejects completion statuses, evidence contents, draft or operation IDs, and submission claims. The [synthetic tests](../../backend/tests/test_agent_extension_tools.py) exercise case isolation, strict inputs, and rejection of fabricated results. Document and form executors are defined by Phases 6 and 7.

## Identifiers and state

| Field | Meaning | Rule |
| --- | --- | --- |
| `thread_id` | Server-issued conversation ID | Owner-scoped; a thread may reference multiple cases. |
| `run_id` | Server-issued attempt to process one message | One active run per case in a thread. Each stopped run retains its actual outcome. |
| `client_message_id` | Client-issued retry key | Unique within a thread; identical retries return the existing run, while a changed body conflicts. |
| `case_id` | Linked case context | Required by the isolated message endpoint. The internal message contract also permits an unbound run. |
| `event_seq` | Server-issued integer, increasing per run | Stable across reconnect; never inferred from arrival order. |
| `proposal_id` | Pending write proposal, once task 38 exists | Bound to owner, case, exact change, expected case revision, and expiry. |

Commit the queued request before acknowledging a message. The worker commits results and ordered events before making them visible. Reconnect reads persisted events after `after_seq`. An exact retry with the same `client_message_id` retrieves the prior run. The exact retention and deletion policy needs task 33 and security review.

## Proposed versioned HTTP surface

The [Phase 5 handoff](phase-04-phase-05-handoff.md) documents the implemented isolated transport and validated wire examples.

All routes are authenticated and private, with `Cache-Control: private, no-store`. IDs are opaque; an inaccessible thread, case, run, or proposal returns the same unavailable result as an unknown ID. Request bodies reject unknown fields and have bounded lengths. The API returns typed errors with a safe `code`, `message`, and `request_id`, without raw tool output or personal data.

| Operation | Proposed route | Request | Response |
| --- | --- | --- | --- |
| Start or continue a linked case | `POST /api/v1/agent/threads/{thread_id}/messages` | `client_message_id`, `text`, `language`, linked `case_id` and optional expected thread revision | HTTP 202 with `run_id` and `accepted_revision` |
| Reply to a clarification | `POST /api/v1/agent/threads/{thread_id}/runs/{run_id}/questions/{question_id}/reply` | `client_reply_id`, expected run revision and text | The stored `question.answered` event. The existing run becomes runnable. |
| Discover active runs | `GET /api/v1/agent/runs/active` | Optional `limit` (1–50) and the previous page’s `before_accepted_at` and `before_run_id` | Owned active runs with thread ID, run ID, optional case ID, status and acceptance time, plus any next cursor |
| Read run | `GET /api/v1/agent/threads/{thread_id}/runs/{run_id}` | None | Current run status, last sequence, and the pending proposal or final result at that boundary |
| Reconnect | `GET /api/v1/agent/threads/{thread_id}/runs/{run_id}/events?after_seq=N` | Last fully rendered sequence | Ordered events, echoed `after_seq`, the last returned sequence and whether more events exist |
| Open a cited passage | `GET /api/v1/agent/threads/{thread_id}/runs/{run_id}/sources/{citation_id}` | Exact citation ID from the saved answer | Current passage text, section and revision, official URL and localized term explanations |
| Stop | `POST /api/v1/agent/threads/{thread_id}/runs/{run_id}/stop` | Expected run revision | Current terminal run snapshot. The event page carries `run.stopped` and its committed operation IDs. |
| Respond to proposal | `POST /api/v1/agent/threads/{thread_id}/runs/{run_id}/proposals/{proposal_id}/decision` | Decision, expected run and case revisions, decision retry key, and a replacement value for a correction | Recorded `approval.decided` event or an explicit conflict or validation error |

An account can request its active runs without a saved thread or run ID. Discovery orders by acceptance time and uses the run ID to order equal timestamps. Copy both fields from `next_cursor` to get the next page. A client with no local event cursor can select a run and begin replay at sequence zero to recover a pending question. Thread creation and the transport for prompt progress (SSE or another bounded stream) need an implementation decision. The event read endpoint is the durable reconnection baseline. An event page advances from `after_seq` to its own `last_event_seq`. An empty page retains the previous cursor. The run snapshot reports the highest currently stored sequence. A long poll or stream may deliver the same envelopes, using the sequence to deduplicate. The frontend must tolerate a disconnected stream without presenting the run as failed or complete.

## Event envelope and result

Every event contains `schema_version`, `thread_id`, `run_id`, `event_seq`, `type`, and `occurred_at`. No event contains raw model reasoning, unrestricted document text, credentials, or hidden reviewer information. The following payloads are proposed:

| Type | Payload | UI meaning |
| --- | --- | --- |
| `run.started` | Accepted message ID | Work has begun; no answer is implied. |
| `progress.updated` | Safe stage label and short text | Informational progress only. |
| `question.requested` | Question ID, text, expected answer shape, relevant missing fields | The run awaits user information. |
| `question.answered` | Question ID, reply retry ID and the owner’s submitted text | The reply was recorded and the run can continue. |
| `approval.requested` | Proposal ID, exact old/new values, rationale, expected revision | The user may review a proposed case change; no write has occurred. |
| `approval.decided` | Proposal ID, proposal event sequence, and the owner's decision | The decision was recorded. A correction opens another review and an acceptance is eligible for the separate write checks. |
| `approval.applied` | Proposal ID, committed operation ID and new case revision | The approved update was saved and the same run can continue. |
| `answer.completed` | `AnswerResult` | Terminal answer with verification status. |
| `run.failed` | Safe error code, retryability, recovery action | Terminal failure; prior committed work remains visible. |
| `run.stopped` | Actual stop outcome and committed operation IDs | Terminal stop; no rollback is implied. |

`AnswerResult` separates `explanation`, `next_action`, `official_channel`, `claims`, `citations`, `missing_information`, and `verification_status`. Each citation contains `citation_id`, `source_id`, `source_version_id`, `passage_id`, `official_url`, publisher, reviewed timestamp, and applicable procedure and location scope. `verification_status` is one of `verified`, `insufficient_evidence`, `conflicting_evidence`, or `unsupported`. An action has separate display copy and a typed operation. The user handles submission in the official channel. Claims about authorities, requirements, fees, dates, or channels must be checked against applicable current approved evidence before `verified` is returned.

## Linking claims to evidence

Task 37.1 adds separate `claims` records for authorities, official channels, mandatory documents, fees, deadlines, conditions, and form versions. Each record carries a bounded statement and at least one versioned passage ID. Those IDs resolve to unique citations in the same answer. Several claims can share a passage, and a claim can link to several passages.

The journal requires at least one linked claim for a new verified answer and a channel claim when an answer exposes an official channel. The reviewed official-assistance path attaches its exact passage to the channel claim, including when the overall answer remains unverified. Historical events retain their stored result and can be replayed with an empty claim list.

Synthetic fixtures cover all seven claim types, dangling or ambiguous references and encrypted journal compatibility.

## Revalidating answer evidence

Task 37.2 reopens every exact citation from the current approved registry before the worker commits an answer, including citations retrieved earlier in the same run. The registry checks the active version, audit history, and passage integrity. The citation must match the registry's publisher, URL, review timestamp, and procedure and location metadata. The source can use a different language from the answer. In PostgreSQL, shared locks on the cited registry rows serialize this check and answer commit against ingestion and review changes.

The internal worker reads a trusted scope in the terminal transaction using the owned thread, run, case, and principal. Each cited passage needs an active, reviewed assignment for the selected procedure and a confirmed location matching the assignment's role and the citation's exact area. If the assignment restricts dates or circumstances, the corresponding confirmed case facts must satisfy those restrictions. When the trusted scope is unavailable, the worker withholds cited claims and official links and preserves the pending case questions. Task 37.4 isolates the effect of a failed citation when the scope is known.

Run `python -m pytest -q tests/test_agent_answer_evidence.py tests/test_agent_candidate_resolution.py` from `backend/`. Synthetic fixtures cover valid revalidation, withdrawal or replacement after retrieval, citation metadata changes, scope mismatches, and replay of the saved answer. A general production reader for reviewed passage assignments remains to be integrated.

## Checking passage support for claims

Task 37.3 checks every consequential claim in the worker's terminal answer. The trusted scope reader supplies active human reviews of specific statements. Each review records the kind and language of the statement, the full supporting passage set, and the reviewed applicability assignment and verbatim quote for each passage. The worker matches the proposed wording and verifies those quotes against the current, applicable passage text from Task 37.2. Multiple passages can support a claim together. The worker requires the full reviewed set. An official channel needs a reviewed channel claim covering the exact link and label exposed in the result.

The worker builds a verified explanation from the matched claim statements and uses localized text for typed next actions. The same support check covers official assistance claims in otherwise unverified results.

Synthetic worker and replay tests cover an official page without the cited deadline, a similar but unreviewed statement, changed channel links, missing joint evidence, and the supported assistance path. Reviews come from the internal reader. Production storage and reviewer authorization for those records remain to be integrated. The implementation checks the integrity and scope of human-reviewed support, with no model call or independent assessment of new paraphrases.

## Publishing answers with partial evidence

Task 37.4 retains each claim whose full reviewed passage set remains current and applicable. It drops a claim if any required link fails and removes citations that support no retained claim. The worker builds the partial explanation from retained statements and localized verification instructions. It records insufficient evidence when a previously verified result loses material and preserves existing conflict or unsupported status. Pending case fields remain attached.

A covered official link stays with its reviewed channel claim. If the proposed channel is missing or unusable in a partial answer, the worker may recover a uniquely supported official channel from independently reviewed passages. The scope reader can supply additional assistance citations for this purpose. Both sets of sources are locked before verification. Every recovered link must pass the same freshness, scope and quote checks, and the displayed wording comes from its review. If several channels remain possible, the worker gives generic verification instructions. If confirmed facts are missing, the next action requests those facts. Otherwise a reviewed channel can be opened to confirm the remaining information.

Synthetic tests verify partial answers in the worker and event replay, including one revoked source alongside a still-supported claim, an unreviewed fee alongside a supported channel, a substituted URL, and missing, ambiguous and available assistance. The optional assistance citations are an internal input to the existing trusted scope reader.

## Preserving information origin

Task 37.5 assigns a typed `origin` to claims, document observations, and proposals. Claims carry `official_source` alongside their exact `evidence_ids`. `next_action` and `approval.requested.proposal` carry `agent_proposal`, including when the suggested action is to open a verified official link. A `document_observations` entry carries `user_document`, a relevant field ID and its review status (`needs_review`, `reviewed`, or `conflict`). Review status describes document metadata. Case facts and public claims keep their existing confirmation and verification rules.

The worker replaces draft observations with a fresh projection of review metadata for the linked, owned case before saving `answer.completed`. It limits the projection to fields relevant to the answer, checkpoint, or active clarification. It uses the existing document consent, scan, expiry, feature and fixture gates. Observations carry field IDs and statuses without values, document IDs, or extracted text. A topic change skips the document read. A case-free run cannot save document observations.

The encrypted journal replays the saved origins through the snapshot and events API. Earlier events lacking the fields derive the origin from their typed structure and have an empty observation list. Synthetic signed-JWT tests cover review status, document removal before answer publication, foreign-case and disabled document access, removal of draft-supplied observations, and owner-only replay. Task 37.6 covers linked source cards and terminology in the user's language.

## Opening exact source cards

Task 37.6 makes each citation in a completed answer open its exact Phase 3 passage in the isolated conversation view. The private endpoint checks ownership and citation membership in the saved result before querying the registry. It uses the saved procedure and location, rechecks the exact version's approval and integrity, and compares canonical citation metadata. A different passage from the same revision, a withdrawn or superseded version, and a request from another account all return unavailable.

The card loads on demand and shows the original passage, its section and revision, and an official page link. A bounded glossary explains terms present in the passage using the language of the stored run. The card preserves the original Italian wording and marks the language of both the passage and explanations. The glossary gives vocabulary meanings. Applicability continues to be checked when publishing claims.

Signed-JWT tests exercise both explanation languages, exact text, citation membership and source withdrawal. The isolated Chromium reconnect scenario opens a card backed by a synthetic approved registry passage and checks the displayed wording and account boundary. Historical events retain their recorded citations for replay. The Phase 4 router and conversation view remain isolated from the production entry points.

## Recording case input provenance

Task 38.1 keeps the origin and review state associated with the existing authoritative record. Accepted messages originate from the authenticated user and stay in the encrypted request. The `question.answered` event carries `user_entered`. Each bounded routing value derived from a reply records that event's sequence in the encrypted checkpoint. A procedure change discards the previous routing values and their references. Routing values apply to the current run. Saved intake changes through its existing explicit confirmation path.

The case intake API pairs its saved values with server-derived `field_provenance`. An entered value keeps `user_entered` as it moves from `draft` to `user_confirmed`. The private-document vault tags each extracted candidate `user_document` and saves the selected candidate ID with the reviewed value's origin. Retaining the suggested value preserves document origin. A user correction carries `user_entered` and keeps the candidate reference and original suggestion. Document review has its own `user_reviewed` state. Both the candidate and its review follow the document's existing protection and lifecycle.

Older intake rows derive provenance from the existing confirmation timestamp. Earlier document reviews derive it from their selected candidate and stored value. Older routing checkpoints still load when they lack reply references. Synthetic tests verify encrypted provenance after reopening, procedure reset, document correction, and separate case confirmation. The schema and input validation of case writes stay compatible with earlier clients. Task 38.2 will present this information with the proposed change.

## Previewing a proposed case change

Task 38.2 gives the internal worker an approval pause alongside the clarification pause. The worker saves the pending proposal ID and the `approval.requested` event in one transaction. The proposal belongs to the case recorded on the owned run. The encrypted journal holds the exact proposal values and rationale.

An owner opening a run sees `pending_proposal` when the run is awaiting approval and its current event is the recorded proposal. The isolated review view displays the affected field, existing value at the recorded revision, proposed value, rationale, expected case revision and proposal ID. It labels an empty existing value and renders the snapshot without deriving a new change from chat text or the current case. A stop clears the proposal from the current view. Historical events remain readable under the existing owner checks.

Signed-JWT and Chromium tests exercise the owner boundary, reload of the exact preview and the saved case value after stopping the run.

## Recording proposal decisions

Task 38.3 records accept, correct, reject and cancel in the isolated owner-scoped transport. The decision must match the pending proposal, the proposal's case revision and the run revision shown to the owner. An exact retry returns its saved decision even after the run advances. A changed decision at the same boundary returns a conflict.

Acceptance records consent to the exact saved proposal. The preview then reports that approval was recorded and the case update is pending. The decision request performs no case write. The write tool requires the matching recorded acceptance for new worker proposals and still requires the existing server-side case revision and authorization checks.

A correction is validated against the field's intake schema or the checklist flag shape. It records the decision and creates a new proposal in the same transaction, with the original existing value and case revision. The owner reviews and accepts that new proposal separately. Reject and cancel end the review and stop the run. Expired proposals can be declined, while acceptance or correction requires an unexpired review.

Signed-JWT tests exercise invalid dates, exact retries, owner isolation and refusal to write declined or replaced proposals. The mobile Chromium scenario corrects a value and accepts the replacement without changing the saved case in the preview.

### Rechecking proposal freshness

Task 38.4 records a dependency snapshot in the encrypted checkpoint. It binds the proposal to the owned case scope, intake and checklist progress read before drafting, and to the exact approved Italian passages retained by the worker or required by the proposal's checklist item. The user-facing preview and decision payload stay the same. A corrected proposal retains the dependencies of the original review.

The isolated write transaction locks the case first, verifies the owned run and the exact accepted decision, and checks the current server-provided case revision. It compares the case snapshot and re-resolves the bound passages through the approved registry while holding shared locks on their sources. A changed or archived case, unavailable or changed passage, or older proposal without a dependency snapshot requires a new review. A rejected write leaves the case and operation receipts untouched. An authorized retry of an already-committed operation returns its original receipt.

Synthetic tests cover edits during drafting and after acceptance, corrections against changed intake, missing evidence, withdrawal, pending revisions and replacement. The check protects the internal write boundary. A production case writer and activation remain separately gated.

### Resuming a LangGraph approval

Task 38.5 saves the actual LangGraph interrupt and its checkpoint with the owner-scoped review event in one transaction. A correction keeps the case and source bindings and saves a new interrupt for the replacement proposal. The graph gate carries identifiers and has no side effects. When the isolated decision transport is explicitly configured with a trusted case revision reader and writer, it commits the owner's decision, then restores the saved interrupt using the same thread ID and passes the exact recorded acceptance to `Command(resume=...)`.

The next transaction revalidates permissions and freshness. It commits the case update, its receipt, the `approval.applied` event and the cleared checkpoint together. The resumed run returns to the saved worker node. The proposal ID is the stable operation key. If execution stops after accepting and before applying, replaying that exact decision resumes from the saved interrupt. If it stops during the write transaction, the transaction rolls back. Reject, cancel and stale inputs cannot call the writer. A stop after a commit reports the existing receipt.

Signed synthetic integration tests recreate the session factory, correct and approve a replacement, simulate a journal failure after the write, retry the decision and continue the worker on the same run. The mobile Chromium scenario exercises review, approval, a single applied event and the updated intake on disposable PostgreSQL. Both integrations use an injected synthetic case writer. Existing pauses from before Task 38.5 can still be reviewed or stopped. Graph resumption requires a proposal prepared with a saved interrupt. Hosted execution and a production case writer are separately gated.

## Failure and concurrency rules

- Invalid message or event cursor: `422`; stale thread or case revision: `409`; unavailable owned resource: `404`; unauthenticated: `401`. Rate and capacity limits use `429` or `503` with retry guidance.
- A thread runs one task at a time and can retain a pending clarification for each linked case. An approval occupies the processing slot. A new message or reply that needs an occupied slot returns `conversation_busy` and preserves the existing runs.
- Submit a clarification with the revision shown when the question was requested. Within that question boundary, retrying with the same ID and trimmed text returns the original event, including after the run advances. An old question or changed reply conflicts. A single-choice reply must match an offered value.
- A catalogue outage or missing applicable passage yields a recoverable, explicitly unverified result. It must not be promoted to a sourced answer by the model.
- A stop request locks the owned run and checks its revision. An already terminal run returns its saved status. The read-only worker stops at the commit boundary and drops outstanding checkpoints and leases. Computation already in progress may return, but its result cannot commit. A queued run can have `run.stopped` as its first event. The current worker performs read-only steps and reports an empty committed operation list. Task 38 must account for any later case writes that commit before cancellation.
- A case revision or source version change invalidates dependent proposals and requires revalidation before approval or reuse.

### Showing the official handoff

Task 38.6 adds a current `handoff` to the owned completed-run snapshot when the recorded answer named an official channel. The server checks that the channel still matches the reviewed claim and exact cited passages. It rechecks the current case scope, active source versions, and reviewed quotes. If the reader is unavailable, the case is archived, or the channel loses support, the snapshot asks the user to verify the channel and omits the actionable link. The recorded answer and event journal retain their original citations.

The English and Italian handoff card displays the next step and the supported destination. Where details remain unresolved, confirming them stays the primary step. The user completes any required sign-in, signing, payment and submission through the official service. Official submission status is unconfirmed in this slice. The channel review and link are preparation evidence. Recording a user report, receipt or authority outcome belongs to the tracking workflow.

Signed tests exercise both languages, unknown submission status, changed case scope, withdrawal and supersession. The mobile Chromium synthetic acceptance displays the verified channel and the user's next step beside the exact source card. The Phase 4 transport and reviewed-scope reader remain isolated.

### Identifying separate goals

Task 39.1 recognizes independently stated English and Italian requests using reviewed names and explicit request cues. Each detected goal carries its own procedure candidate IDs, place candidate IDs and missing procedure or location fields. The order follows the message. A location attached to one goal does not fill another goal's gap. Reviewed names remain intact across punctuation and conjunctions. Repeated aliases and alternatives can remain part of the same request.

The encrypted worker checkpoint and owned terminal result carry up to six candidate groups, with up to ten procedure IDs and ten place IDs per group. The checkpoint carries IDs and missing fields without copying raw goal text. Oversized or insufficiently separated requests fall back to clarification. An independently stated request with no reviewed match remains a separate goal with an empty procedure list. A place mention remains a candidate and does not establish jurisdiction or authority.

The current worker records the groups before applying any case facts or resolving authorities across them. The isolated snapshot and event replay preserve the same groups. Synthetic tests cover both languages, unknown procedures, distinct locations, repeated aliases, alternatives, negation, overflow, checkpoint encryption and authenticated replay.

### Choosing the active task

Task 39.2 checks for an explicit starting preference by a numbered goal or an exact, unique reviewed procedure name. It preserves requests listed with a starting cue. If the preference is missing, conflicting, or matches more than one goal, the worker asks a single-choice question in the user's language. Options keep message order. Reviewed procedure and place labels help distinguish them, with a numbered fallback where labels are unavailable.

The existing owner-scoped reply endpoint binds a choice to the pending question and run revision. The encrypted journal records the selected number and its original option text. Exact retries preserve the choice. Invalid options, stale replies, uncertainty and skipping cannot select an active task. The snapshot and resumed result display the same selected task.

Synthetic tests cover clear and ambiguous preferences, an unauthorized or invalid reply, exact retry, selection display and skip. The mobile Chromium scenario reopens the question, selects a task, and sees the active choice after the worker resumes.

If the selected marriage-banns task has no compatible saved case, the worker asks a free-text follow-up for the two municipality roles. The question records the existing selection as `procedure_goal`. The snapshot presents it while waiting for the reply and after it is accepted. The reply stays with that task and grants no evidence or new case binding.

### Verifying the internal task resolved from conversation (legacy storage name: case)

Task 39.3 verifies an explicitly selected case against the authenticated owner, active record and current conversation link. A relative reference such as “the other application” excludes the existing case binding when one is present and asks the user to choose. A selected goal narrows the case choices by its procedure candidates. A goal pointing exclusively to a different location does not inherit the saved Milan procedure. Options display numbered short references and creation dates. Oversized lists and missing matches direct the user to their saved cases.

The reply endpoint binds the selected label to the case ID recorded on the pending question and current revision. It checks the link and active state again before writing the reply. The worker rechecks availability before completing, and the current snapshot removes a case link that is no longer active. Selecting a case leaves the original run's case binding intact. The user can open the independently verified case and continue from it.

Signed tests cover both languages, separate active-goal procedure candidates, explicit selection, cross-account access, archive races and new-run binding. The mobile synthetic Chromium scenario answers an **in-chat clarification question** to disambiguate the target; the authenticated API validates the internal task reference without exposing a user-facing case.

### Reusing confirmed shared facts

Task 39.4 lets the isolated candidate resolver reuse the confirmed citizenship category when the owner continues with an independently bound individual Milan case in the same conversation. Only active individual cases with valid confirmed intake can supply the field. The target must be in the individual scope and have no citizenship entry of its own. If the source values disagree, the worker leaves the field open. An explicit conflicting statement in the current message prompts for clarification. A reply applies to the current run.

The worker projects only that category and rechecks it before committing the routing step. Dates, locations, housing, registration and household details, document observations and official evidence continue to use the current case's own scope. Reuse is a routing input. The saved intake and its confirmation are written through the existing case flow, and approved evidence still requires the current case to meet its own requirements.

The [signed API and worker tests](../../backend/tests/test_agent_shared_case_facts.py) cover a verified case selection followed by a new bound run, draft and archived sources, unrelated accounts and conversations, conflicting values and revocation during a worker step.

### Switching between pending case tasks

**Legacy API behavior (not permitted customer UX):** Task 39.5 currently lists active saved records through an internal conversation endpoint and accepts an explicitly bound case ID when starting a new run. These APIs remain owner-scoped during migration. Under D-010, the **customer must not be offered a cases/tasks selector**; a natural-language message or inline clarification resolves the relevant internal task without exposing the ID. This agent-driven routing and resumption remain hosted acceptance work, not an implemented claim. The browser opens each saved run through its existing snapshot and event cursor. Reloading preserves the pending question ID, revision, options and checkpoint for the selected run.

Migration `20261119_0024` allows one active run per case and one processing slot per conversation. Queued work, running work and pending approvals occupy that slot. A reply or new message that would compete for it returns `conversation_busy`, and the original question remains available. Existing replies and message retries retain their idempotency. The downgrade requires one active run per conversation again. Finish or stop extra active runs before downgrading.

Signed API tests exercise reopening two pending tasks, rejection of an unavailable case or mismatched question, and exact retries. Disposable PostgreSQL tests exercise competing replies. The synthetic browser scenario exercises two internally bound runs **without a visible case picker**, returns to it after reload, and answers it while the other question remains pending.

### Testing isolation between pending cases

The [cross-case integration test](../../backend/tests/test_agent_cross_case_isolation.py) opens two runs in one signed synthetic conversation. The private vault receives two PDFs with the same filename, different dates, and different review states. The worker derives each question from the corresponding case's review state. Both reply orders are exercised. A question ID from the other case is rejected, and answering one question leaves the other run's event journal intact.

The isolated evidence fixture covers Milano and Como with distinct versioned passages and overlapping effective periods. The worker is offered both passages for each answer. The scope check retains only the current municipality's citation. Each source card and document review stays bound to its own run or case. The Como assignment exists only in the test database. Run from `backend/` with `python -m pytest -q tests/test_agent_cross_case_isolation.py`.

## Acceptance and dependency checks

The [wire models](../../backend/app/agent/contract.py) encode bounded inputs, typed events, run results and pagination invariants. The [synthetic fixtures](../../backend/tests/test_agent_contract.py) cover verified and conflicting answers, clarification, approval requests, stop, failure, citation identity, and reconnection. The [encrypted acceptance service](../../backend/app/agent/run_requests.py) now persists a queued run with the message before its caller commits. The [local fixtures](../../backend/tests/test_agent_run_requests.py) cover retry recovery, changed payload conflicts, stale revisions, case permissions and verified ciphertext. A retry can carry a fresher thread revision because revisions are concurrency metadata; the message identity is the text, language and optional case within its thread.

Run the checks from `backend/` with `python -m pytest -q tests/test_agent_contract.py`. These checks validate payload shape and sequence. Serving a verified result still requires server-side authorization and applicable approved evidence. The internal service has its own ownership and idempotency tests. The [encrypted journal](../../backend/app/agent/run_events.py) replays committed events through the cursor contract and uses the event sequence plus one as the run revision. Repeated writes of the same event return the saved event, and the run status changes in the same transaction as the new event. Stored terminal results describe the original run. Future presentation must revalidate source freshness before treating an old answer as current guidance. The [internal worker checkpoint](../../backend/app/agent/checkpoints.py) can be committed with its next nonterminal event. A save compares the previously read checkpoint revision and event sequence before updating. The [internal worker](../../backend/app/agent/worker.py) reopens the saved request and checkpoint, runs a read-only step outside the database transaction, and commits through the checkpoint revision and event watermark. A terminal answer removes the checkpoint in its own commit. The internal scheduler claims a runnable run with an expiring, server-issued lease. Execution and result writes both check the current token. PostgreSQL queue reads skip rows locked by other claimers. An expired worker can no longer commit, and a new worker can reclaim the work. The worker can atomically pause for a clarification. The internal reply handler locks the owned run, validates the question boundary and records its encrypted reply with the resumption checkpoint. The first resumed step can read that reply after a restart. The [isolated HTTP router](../../backend/app/agent/reconnect_router.py) serves active run discovery, run snapshots, bounded event replay, clarification replies, and stop requests. The [signed-JWT test](../../backend/tests/test_agent_reconnect_http.py) discovers the saved run with only the owner’s signed identity, answers its question, resumes the worker and reads its terminal answer. It also covers the owner boundary, deleted cases, non-cacheable responses, and safe errors. The default ASGI application leaves these routes unmounted. Hosted scheduling, frontend integration, committed-write reporting for future case tools, and live stream resumption still require integration.

Before the first graph or public route, Phase 3 must expose approved, versioned, scope-filtered catalogue evidence and a reviewed pilot workflow. Task 33 must decide event/checkpoint retention and deletion. Task 38 must implement server-authorised, revision-checked approvals before the approval endpoint can be enabled. Keep production agent and document surfaces disabled until their respective gates pass.
