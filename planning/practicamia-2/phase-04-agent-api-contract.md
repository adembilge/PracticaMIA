# Phase 4.31 — proposed agent API and interface contract

**Status:** proposed contract with offline schemas and synthetic tests. Active run discovery, run reads, event replay, clarification replies, and stop requests have isolated authenticated HTTP coverage. Hosted routes, live streaming, approval operations, and production capability remain pending. The persistence and worker evidence is recorded below. The Phase 3 catalogue and reviewed multi-authority pilot set are not ready for an agent integration. The existing Milan assistant and synthetic preparation chat remain separate.

## Scope and trust boundary

The backend owns thread and run state, authorises every case reference against the authenticated principal, and validates evidence and operations before returning them as verified. A model may suggest an intent, question, or action; it cannot approve a source, select an unsupported jurisdiction as fact, commit a case change, or report official submission. The frontend renders typed server events and never treats a progress message as a completed action.

The first implementation slice may answer from currently approved passages and ask for missing context. Case writes need the later proposal and approval contract in task 38. Document tools remain unavailable until their release gates pass. Phase 3 must supply a typed catalogue response with procedure, authority role, service area, channel, source version, passage, and applicability result before sourced multi-authority answers can be enabled.

## Identifiers and state

| Field | Meaning | Rule |
| --- | --- | --- |
| `thread_id` | Server-issued conversation ID | Owner-scoped; a thread may reference multiple cases. |
| `run_id` | Server-issued attempt to process one message | One active run per thread; a stopped run retains its actual outcome. |
| `client_message_id` | Client-issued retry key | Unique within a thread; identical retries return the existing run, while a changed body conflicts. |
| `case_id` | Optional case context | Checked against the principal on every read and tool call. |
| `event_seq` | Server-issued integer, increasing per run | Stable across reconnect; never inferred from arrival order. |
| `proposal_id` | Pending write proposal, once task 38 exists | Bound to owner, case, exact change, expected case revision, and expiry. |

Store the authoritative result and ordered events before acknowledging a run. A reconnect reads persisted events after `after_seq`; it does not replay model or tool calls. A retry uses the same `client_message_id` to retrieve the prior run and cannot create a second write. The exact retention and deletion policy needs task 33 and security review.

## Proposed versioned HTTP surface

All routes are authenticated and private, with `Cache-Control: private, no-store`. IDs are opaque; an inaccessible thread, case, run, or proposal returns the same unavailable result as an unknown ID. Request bodies reject unknown fields and have bounded lengths. The API returns typed errors with a safe `code`, `message`, and `request_id`, without raw tool output or personal data.

| Operation | Proposed route | Request | Response |
| --- | --- | --- | --- |
| Start or continue | `POST /api/v1/agent/threads/{thread_id}/messages` | `client_message_id`, `text`, `language`, optional `case_id` and expected thread revision | `thread_id`, `run_id`, `status`, `last_event_seq` |
| Reply to a clarification | `POST /api/v1/agent/threads/{thread_id}/runs/{run_id}/questions/{question_id}/reply` | `client_reply_id`, expected run revision and text | The stored `question.answered` event. The existing run becomes runnable. |
| Discover active runs | `GET /api/v1/agent/runs/active` | Optional `limit` (1–50) and the previous page’s `before_accepted_at` and `before_run_id` | Owned active runs with thread ID, run ID, optional case ID, status and acceptance time, plus any next cursor |
| Read run | `GET /api/v1/agent/threads/{thread_id}/runs/{run_id}` | None | Current run status, final result if present, and last sequence |
| Reconnect | `GET /api/v1/agent/threads/{thread_id}/runs/{run_id}/events?after_seq=N` | Last fully rendered sequence | Ordered events, echoed `after_seq`, the last returned sequence and whether more events exist |
| Stop | `POST /api/v1/agent/threads/{thread_id}/runs/{run_id}/stop` | Expected run revision | Current terminal run snapshot. The event page carries `run.stopped` and its committed operation IDs. |
| Respond to proposal | `POST /api/v1/agent/threads/{thread_id}/proposals/{proposal_id}/decision` | `accept`, `correct`, `reject`, or `cancel`, expected case revision, decision retry key | Applied revision or explicit conflict/expired/invalid status; task 38 only |

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
| `answer.completed` | `AnswerResult` | Terminal answer with verification status. |
| `run.failed` | Safe error code, retryability, recovery action | Terminal failure; prior committed work remains visible. |
| `run.stopped` | Actual stop outcome and committed operation IDs | Terminal stop; no rollback is implied. |

`AnswerResult` separates `explanation`, `next_action`, `official_channel`, `citations`, `missing_information`, and `verification_status`. Each citation contains `citation_id`, `source_id`, `source_version_id`, `passage_id`, `official_url`, publisher, reviewed timestamp, and applicable procedure and location scope. `verification_status` is one of `verified`, `insufficient_evidence`, `conflicting_evidence`, or `unsupported`. An action has separate display copy and a typed operation; an official link is not an executable submission operation. Claims about authorities, requirements, fees, dates, or channels must be checked against applicable current approved evidence before `verified` is returned.

## Failure and concurrency rules

- Invalid message or event cursor: `422`; stale thread or case revision: `409`; unavailable owned resource: `404`; unauthenticated: `401`. Rate and capacity limits use `429` or `503` with retry guidance.
- Only one active run per thread. A concurrent different message returns a conflict rather than silently replacing the pending question or approval.
- Submit a clarification with the revision shown when the question was requested. Within that question boundary, retrying with the same ID and trimmed text returns the original event, including after the run advances. An old question or changed reply conflicts. A single-choice reply must match an offered value.
- A catalogue outage or missing applicable passage yields a recoverable, explicitly unverified result. It must not be promoted to a sourced answer by the model.
- A stop request locks the owned run and checks its revision. An already terminal run returns its saved status. The read-only worker stops at the commit boundary and drops outstanding checkpoints and leases. Computation already in progress may return, but its result cannot commit. A queued run can have `run.stopped` as its first event. The current worker performs read-only steps and reports an empty committed operation list. Task 38 must account for any later case writes that commit before cancellation.
- A case revision or source version change invalidates dependent proposals and requires revalidation before approval or reuse.

## Acceptance and dependency checks

The [wire models](../../backend/app/agent/contract.py) encode bounded inputs, eight typed events, run results and pagination invariants. The [synthetic fixtures](../../backend/tests/test_agent_contract.py) cover verified and conflicting answers, clarification, approval requests, stop, failure, citation identity, and reconnection. The [encrypted acceptance service](../../backend/app/agent/run_requests.py) now persists a queued run with the message before its caller commits. The [local fixtures](../../backend/tests/test_agent_run_requests.py) cover retry recovery, changed payload conflicts, stale revisions, case permissions and verified ciphertext. A retry can carry a fresher thread revision because revisions are concurrency metadata; the message identity is the text, language and optional case within its thread.

Run the checks from `backend/` with `python -m pytest -q tests/test_agent_contract.py`. These checks validate payload shape and sequence. Serving a verified result still requires server-side authorization and applicable approved evidence. The internal service has its own ownership and idempotency tests. The [encrypted journal](../../backend/app/agent/run_events.py) replays committed events through the cursor contract and uses the event sequence plus one as the run revision. Repeated writes of the same event return the saved event, and the run status changes in the same transaction as the new event. Stored terminal results describe the original run. Future presentation must revalidate source freshness before treating an old answer as current guidance. The [internal worker checkpoint](../../backend/app/agent/checkpoints.py) can be committed with its next nonterminal event. A save compares the previously read checkpoint revision and event sequence before updating. The [internal worker](../../backend/app/agent/worker.py) reopens the saved request and checkpoint, runs a read-only step outside the database transaction, and commits through the checkpoint revision and event watermark. A terminal answer removes the checkpoint in its own commit. The internal scheduler claims a runnable run with an expiring, server-issued lease. Execution and result writes both check the current token. PostgreSQL queue reads skip rows locked by other claimers. An expired worker can no longer commit, and a new worker can reclaim the work. The worker can atomically pause for a clarification. The internal reply handler locks the owned run, validates the question boundary and records its encrypted reply with the resumption checkpoint. The first resumed step can read that reply after a restart. The [isolated HTTP router](../../backend/app/agent/reconnect_router.py) serves active run discovery, run snapshots, bounded event replay, clarification replies, and stop requests. The [signed-JWT test](../../backend/tests/test_agent_reconnect_http.py) discovers the saved run with only the owner’s signed identity, answers its question, resumes the worker and reads its terminal answer. It also covers the owner boundary, deleted cases, non-cacheable responses, and safe errors. The default ASGI application leaves these routes unmounted. Hosted scheduling, frontend integration, committed-write reporting for future case tools, and live stream resumption still require integration.

Before the first graph or public route, Phase 3 must expose approved, versioned, scope-filtered catalogue evidence and a reviewed pilot workflow. Task 33 must decide event/checkpoint retention and deletion. Task 38 must implement server-authorised, revision-checked approvals before the approval endpoint can be enabled. Keep production agent and document surfaces disabled until their respective gates pass.
