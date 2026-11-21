# Phase 4 agent API handoff for Phase 5

The isolated FastAPI transport supports first and subsequent case-free chat messages, optional case-bound messages, persisted events, clarifications, saved proposals and current source cards. It is mounted in signed synthetic API and Chromium acceptance harnesses. The default application leaves the routes unmounted. Hosted transport and worker, complete terminal conversation history, and verified account-session handling remain open.

The examples use synthetic IDs, times and URLs. They omit optional fields with default values where those fields do not affect the example. The [agent contract](phase-04-agent-api-contract.md) describes the broader design and security checks.

## Endpoint map

Use `/api/v1/agent` as the FastAPI prefix. In the paths below, `T` is a thread UUID and `R` is a run UUID. The browser acceptance harness maps its local `/api/agent` requests to those routes.

| Method and path | Read or write boundary |
| --- | --- |
| `GET /runs/active` | Owned active runs. Pass both `before_accepted_at` and `before_run_id` from `next_cursor` when paging. |
| `GET /runs/recent` | Owned active and completed/failed/stopped runs, newest first, paginated with the same timestamp/run-ID cursor. Metadata only; no message text. |
| `GET /threads/T/history` | Owner-only, up to 30 accepted turns per page, oldest-to-newest within the page. Includes decrypted user messages, question/answer pairs, proposal/decision history, confirmed write receipts, and terminal results. For `failed` or `stopped`, `terminal_event` reproduces the authenticated final `run.failed` or `run.stopped` event, even when the compact event scan is truncated. Older pages use `before_revision`. |
| `POST /conversations` | Start a thread and queue the first message in one transaction. The first interaction needs only `client_message_id`, `text` and `language`. |
| `GET /threads/T/cases` | Linked active cases, their active run IDs and any unbound run. Use `after_case_id` with `next_case_id` to page cases. |
| `POST /threads/T/messages` | Continue the same conversation after a completed run, with an optional owned `case_id`; return an idempotent 202 receipt. |
| `GET /threads/T/runs/R` | Read the latest status, revision and any pending proposal, result or current handoff. |
| `GET /threads/T/runs/R/events` | Read persisted events after `after_seq`, with up to 100 events per page. |
| `POST /threads/T/runs/R/questions/Q/reply` | Record a reply to the displayed question at its run revision. |
| `POST /threads/T/runs/R/proposals/P/decision` | Record a decision against the displayed proposal and its run and case revisions. |
| `GET /threads/T/runs/R/sources/C` | Recheck the exact citation `C` in the owned run's saved answer. |
| `POST /threads/T/runs/R/stop` | Stop the run at the supplied revision and return the resulting snapshot. |

The routes require an authenticated owner and return `Cache-Control: private, no-store`. Read current status from the server after account changes. Clear the previous account's displayed conversations, pending operations and source views. Recent-run discovery never returns decrypted text; the history endpoint decrypts only inside an owned thread and includes only still-authorised linked cases. Full question/answer events for a particular run remain behind its existing run event journal endpoint.

## Send a message

Use `POST /conversations` from the initial composer. The 202 receipt includes `thread_id`, `run_id` and `accepted_revision`. Use the returned thread and run to open the conversation and recover it after reload. No case ID or thread revision is required at this step.

Use `POST /threads/T/messages` for every subsequent free-text message in the **same** chat. The `case_id` is optional: omit it for a general follow-up or a new topic; supply only a case already linked to and owned by this conversation for a case-specific action. The request is rejected while a conflicting run is active; finish, reply to, or stop the active run before sending an unbound follow-up. Generate a `client_message_id` once for each submission. If the client loses the receipt, resend the same ID with the same text, language and case scope. An identical replay returns the original receipt even after the run advances. An edited submission needs a new ID. Use `expected_thread_revision` only when the client has a confirmed revision for the thread.

<!-- wire: message -->
```json
{
  "client_message_id": "50000000-0000-4000-8000-000000000004",
  "case_id": "50000000-0000-4000-8000-000000000003",
  "text": "Which office handles this synthetic case?",
  "language": "en",
  "expected_thread_revision": 1
}
```

HTTP 202 returns the accepted run and thread revision. The worker commits the result later.

<!-- wire: receipt -->
```json
{
  "run_id": "50000000-0000-4000-8000-000000000002",
  "accepted_revision": 2
}
```

## Restore a completed chat and its earlier turns

When opening the chatbot after a browser restart, retrieve `GET /runs/recent`. Unlike `/runs/active`, it also includes finished runs, so the user can reopen a past conversation without remembering a run ID. This endpoint returns **runs**, not distinct conversations: group the returned page by `thread_id`, retain the newest entry, and omit any thread whose latest run is active or already appears in active-run discovery. Earlier turns belong in that thread's in-chat history, not separate "Past conversations" entries. The current isolated browser view deduplicates one bounded page; loading additional pages for a comprehensive older-conversation switcher remains open. Keep this in the **same chat UI**, not a separate page. The list contains metadata only. Once an owner selects a run, fetch its current snapshot and `GET /threads/T/history` to display user messages, recorded question/reply exchanges, and completed answers in order. Within each run, sort clarification and approval cards by their **persisted request `event_seq`**, not by card type; the applied receipt and decision remain associated with the original proposal. Missing question replies must not be synthesized. Use `before_revision` to load older turns. Pending unanswered prompts remain in the run snapshot, not fabricated as completed exchanges. The compact history projection scans at most 256 encrypted events per run and marks `clarification_history_truncated` and `approval_history_truncated` when more exist; the per-run event journal remains available for full paging. Each approval is reconstructed from the original `approval.requested` proposal, its optional matching `approval.decided` event, and only when present its `approval.applied` receipt (operation ID and committed case revision). **Never display 'saved' for a proposal or an 'accept' decision alone.** Correction creates a new review proposal; rejecting or cancelling never produces an applied receipt. After a failed or interrupted accepted proposal, show 'accepted; no saved update confirmed' unless its exact `approval.applied` event exists. When a run fails, show only its typed safe code and recorded retry/recovery policy, never a provider exception or an invented answer; an explicit retry is a **new run** in the same conversation and must not replace the failed attempt in history. When a run is stopped, use `run.stopped.committed_operation_ids` to distinguish no confirmed case writes from earlier committed operations that remain saved. Do not imply a stop rolls back earlier receipts. Terminal answers may be revalidated by opening their run snapshots and cited source cards. The run journal remains authoritative for complete administrative event history.

The history view does not create a new chat or silently restore an old case. A new free-text question to `/threads/T/messages` uses the same thread ID; case-scoped operations still require the relevant owned case. Deleted case links and different-account threads are unavailable. This API is mounted only in the isolated acceptance harness until the hosted agent and session wiring are approved.

## Restore a run and read a question

1. Reopen a known authorised run by ID. With no run ID, start at `GET /runs/active`. Terminal runs require a known run ID. Use the linked case list to choose the active task in a multi-case thread.
2. Fetch the snapshot, then recover events from the last fully rendered sequence for this run. Start at zero for a fresh view. Advance the cursor to the page's `last_event_seq` after applying the page and continue while `has_more` is true. An empty page preserves the previous cursor.
3. Deduplicate by `(run_id, event_seq)`. Use the snapshot as the current state and older events as history. If a pending question changes between reads, reload before rendering or submitting its form. A disconnected client can resume polling from the saved cursor.

<!-- wire: active-runs -->
```json
{
  "items": [{
    "thread_id": "50000000-0000-4000-8000-000000000001",
    "run_id": "50000000-0000-4000-8000-000000000002",
    "case_id": "50000000-0000-4000-8000-000000000003",
    "status": "waiting_for_information",
    "accepted_at": "2026-11-20T09:00:00Z"
  }],
  "next_cursor": null
}
```

The snapshot has `status: waiting_for_information`, `last_event_seq: 2`, and `run_revision: 3`. Read the question at sequence 2. The example uses `GET /events?after_seq=0&limit=2`.

<!-- wire: pending-events -->
```json
{
  "thread_id": "50000000-0000-4000-8000-000000000001",
  "run_id": "50000000-0000-4000-8000-000000000002",
  "after_seq": 0,
  "events": [
    {
      "schema_version": 1,
      "thread_id": "50000000-0000-4000-8000-000000000001",
      "run_id": "50000000-0000-4000-8000-000000000002",
      "event_seq": 1,
      "occurred_at": "2026-11-20T09:00:01Z",
      "type": "run.started",
      "client_message_id": "50000000-0000-4000-8000-000000000004"
    },
    {
      "schema_version": 1,
      "thread_id": "50000000-0000-4000-8000-000000000001",
      "run_id": "50000000-0000-4000-8000-000000000002",
      "event_seq": 2,
      "occurred_at": "2026-11-20T09:00:02Z",
      "type": "question.requested",
      "question": {
        "question_id": "50000000-0000-4000-8000-000000000005",
        "text": "Which synthetic municipality applies?",
        "answer_shape": "single_choice",
        "options": ["Fixture A", "Fixture B"],
        "missing_fields": ["destination"]
      }
    }
  ],
  "last_event_seq": 2,
  "has_more": false
}
```

Render `single_choice` from the exact options. For `free_text`, use `answer_format` and `reply_hint` when provided. For saved-case and task choices, use the typed metadata on the question and server-projected selection on the run. Submit the question ID in the path and the displayed `run_revision` in the body. The `unknown`, `skip` and `change_topic` dispositions omit `text`.

<!-- wire: reply -->
```json
{
  "client_reply_id": "50000000-0000-4000-8000-000000000008",
  "expected_run_revision": 3,
  "disposition": "answer",
  "text": "Fixture B"
}
```

The reply returns the stored `question.answered` event. A lost response can be retried with the same ID, question, revision and payload. The user can continue on the same run once the worker advances it.

## Read a verified answer and open its source

After the reply, resume at `after_seq=2`. The third event records the reply. The fourth carries the terminal answer. The receipt for a reply or a progress event only confirms that boundary. Render the final answer when `answer.completed` is available or the snapshot exposes it.

<!-- wire: answer-events -->
```json
{
  "thread_id": "50000000-0000-4000-8000-000000000001",
  "run_id": "50000000-0000-4000-8000-000000000002",
  "after_seq": 2,
  "events": [
    {
      "schema_version": 1,
      "thread_id": "50000000-0000-4000-8000-000000000001",
      "run_id": "50000000-0000-4000-8000-000000000002",
      "event_seq": 3,
      "occurred_at": "2026-11-20T09:00:05Z",
      "type": "question.answered",
      "question_id": "50000000-0000-4000-8000-000000000005",
      "client_reply_id": "50000000-0000-4000-8000-000000000008",
      "disposition": "answer",
      "text": "Fixture B"
    },
    {
      "schema_version": 1,
      "thread_id": "50000000-0000-4000-8000-000000000001",
      "run_id": "50000000-0000-4000-8000-000000000002",
      "event_seq": 4,
      "occurred_at": "2026-11-20T09:00:06Z",
      "type": "answer.completed",
      "result": {
        "explanation": "The example service is the channel for this synthetic case.",
        "verification_status": "verified",
        "next_action": {"label": "Open the official channel", "operation": "open_official_channel"},
        "official_channel": {"label": "Synthetic service", "url": "https://example.invalid/service"},
        "claims": [{
          "kind": "channel",
          "statement": "The example service is the channel for this synthetic case.",
          "evidence_ids": ["50000000-0000-4000-8000-000000000007:0003"]
        }],
        "citations": [{
          "citation_id": "50000000-0000-4000-8000-000000000007:0003",
          "passage_id": "50000000-0000-4000-8000-000000000007:0003",
          "source_version_id": "50000000-0000-4000-8000-000000000007",
          "source_id": "synthetic-service",
          "official_url": "https://example.invalid/source",
          "publisher": "Synthetic publisher",
          "reviewed_at": "2026-11-20T08:00:00Z",
          "procedure_id": "synthetic-procedure",
          "location_id": "synthetic-area"
        }]
      }
    }
  ],
  "last_event_seq": 4,
  "has_more": false
}
```

Place citation controls by the claim they support. Use the exact `citation_id` from the answer, URL-encoded as a path parameter. Open the cited passage with `GET /sources/{citation_id}`. The reader returns the exact currently approved passage or a safe 404.

<!-- wire: source-card -->
```json
{
  "title": "Synthetic service guide",
  "source_language": "it",
  "explanation_language": "en",
  "passage": {
    "citation": {
      "citation_id": "50000000-0000-4000-8000-000000000007:0003",
      "passage_id": "50000000-0000-4000-8000-000000000007:0003",
      "source_version_id": "50000000-0000-4000-8000-000000000007",
      "source_id": "synthetic-service",
      "official_url": "https://example.invalid/source",
      "publisher": "Synthetic publisher",
      "reviewed_at": "2026-11-20T08:00:00Z",
      "procedure_id": "synthetic-procedure",
      "location_id": "synthetic-area"
    },
    "source_revision": 1,
    "section_path": "Servizio di esempio",
    "content": "Passaggio sintetico sul cambio di residenza."
  },
  "terms": [{
    "term": "cambio di residenza",
    "explanation": "Updating the address recorded for your registered residence."
  }]
}
```

Show the original passage and explanatory terms separately. Preserve the saved citation reference if the passage becomes unavailable. Use the refreshed snapshot's `handoff` for current channel actions. Enable the channel link only when its operation is `open_official_channel` with current evidence. A `verification_required` handoff asks the user to verify the channel. The user handles official sign-in, payment, signing and submission, with `submission_status: unconfirmed` throughout this handoff.

## Review and apply a proposal

This separate synthetic run is paused after an `approval.requested` at sequence 2. The snapshot's `pending_proposal` is the authoritative card payload.

<!-- wire: approval-snapshot -->
```json
{
  "thread_id": "50000000-0000-4000-8000-000000000001",
  "run_id": "50000000-0000-4000-8000-000000000009",
  "status": "waiting_for_approval",
  "last_event_seq": 2,
  "run_revision": 3,
  "pending_proposal": {
    "proposal_id": "50000000-0000-4000-8000-000000000006",
    "case_id": "50000000-0000-4000-8000-000000000003",
    "field_id": "move_in_date",
    "previous_value": "2026-11-15",
    "proposed_value": "2026-11-16",
    "rationale": "The user confirmed the corrected date in this synthetic example.",
    "expected_case_revision": 7,
    "expires_at": "2026-11-20T09:10:00Z",
    "origin": "agent_proposal"
  }
}
```

Post to `/proposals/{proposal_id}/decision` with the displayed run and case revisions. For `correct`, supply `corrected_value`, reload and show the replacement proposal for its own decision. For `accept`, `reject` and `cancel`, omit the replacement value. An exact retry of the decision replays its stored event.

<!-- wire: approval -->
```json
{
  "decision": "accept",
  "expected_run_revision": 3,
  "expected_case_revision": 7,
  "client_decision_id": "50000000-0000-4000-8000-000000000010"
}
```

HTTP 200 returns the stored decision.

<!-- wire: approval-decided -->
```json
{
  "schema_version": 1,
  "thread_id": "50000000-0000-4000-8000-000000000001",
  "run_id": "50000000-0000-4000-8000-000000000009",
  "event_seq": 3,
  "occurred_at": "2026-11-20T09:01:00Z",
  "type": "approval.decided",
  "proposal_id": "50000000-0000-4000-8000-000000000006",
  "proposal_event_seq": 2,
  "decision": {
    "decision": "accept",
    "expected_case_revision": 7,
    "client_decision_id": "50000000-0000-4000-8000-000000000010"
  }
}
```

While `approval_recorded` is true and no proposal is pending, show the recorded decision as waiting for application. Show “Saved” only after reading the committed receipt in `approval.applied`. With the isolated writer configured and its checks satisfied, the next event would be the following.

<!-- wire: approval-applied -->
```json
{
  "schema_version": 1,
  "thread_id": "50000000-0000-4000-8000-000000000001",
  "run_id": "50000000-0000-4000-8000-000000000009",
  "event_seq": 4,
  "occurred_at": "2026-11-20T09:01:01Z",
  "type": "approval.applied",
  "proposal_id": "50000000-0000-4000-8000-000000000006",
  "operation_id": "50000000-0000-4000-8000-000000000011",
  "case_revision": 8
}
```

An outdated case or evidence can require a fresh proposal review. Read the current snapshot and journal after approval and before updating the case UI. A stop sends `expected_run_revision`. The persisted `run.stopped` event exposes already committed operation IDs.

## Errors and capability decisions

| State | Integration behaviour |
| --- | --- |
| Network loss or uncertain response | Preserve the current in-memory request. Resend the same pending request with its existing client ID or replay the run from its cursor. |
| `401 unauthenticated` | Restore the authenticated session before reconnecting. |
| `404 unavailable` | Close or disable the unavailable item and use the current account's list. A source can be unavailable after revocation or replacement. |
| `409 stale_question`, `stale_proposal` or `stale_run` | Reload the affected run and show the current boundary before a new action. |
| `409 stale_thread`, `message_conflict` or `conversation_busy` | Restore the thread state. Use a new message ID for an edited submission. Wait for a busy run to pause or finish. |
| `422 invalid_reply`, `invalid_proposal_value` or `invalid_cursor` | Preserve the editable draft and show the validation guidance. Resume an invalid cursor from a known server sequence. |
| Persisted `run.failed` | Show the safe recovery value from the event. For `retry_later`, a fresh request uses a new message ID after the service recovers. For `review_proposal`, reload the current case and request a fresh review. |

The browser fixture demonstrates consecutive free-text turns in one thread, saved-case switching, cursor replay, lost acknowledgements, source display, restored clarification and approval history, safe failure/stopped outcomes, and a case-write receipt shown inline only after the committed operation. It uses temporary signed identities, an isolated worker and a disposable database. Hosted scheduling, streaming, account-session acceptance, production case writes, full administrative event rendering, and broader catalogue and pilot verification remain gated. The development replay and latency samples describe the isolated system. See the [acceptance scenarios](../../docs/ACCEPTANCE_TESTING.md#acceptance-scenarios) and [Phase 4 evaluation results](phase-04-agent-and-conversation-engine.md#40-evaluate-the-agent-and-close-phase-4).

From `backend/`, verify the examples against the wire models with `python -m pytest -q tests/test_agent_contract.py -k phase5_handoff`. For runtime behaviour, run `python -m pytest -q tests/test_agent_reconnect_http.py tests/test_agent_recovery_http.py tests/test_agent_source_cards.py tests/test_agent_approval_resume.py`. The browser reference is the existing [acceptance client](../../frontend/tests/acceptance/agent-reconnect.tsx).
