# Milan residence-change pilot

## Session

Ask a few participants familiar with the supported Milan renter scenario to work through a fictional case in the protected Preview. Obtain the participant's agreement to record anonymous usability observations. Use the signed first-route configuration and a dedicated account. Give the participant the following fictional brief without explaining the interface.

> An adult Italian citizen already registered in Italy moves alone to Comune di Milano. The citizen holds a registered private rental contract and will not join an existing household. Use the example move date 5 November 2026.

1. Start a saved case and answer the scope and case-detail prompts.
2. Read the reviewed actions. Leave and reopen the case, then continue from the saved state.
3. Open the PDF summary and download it. Use whichever of English and Italian the participant prefers.
4. Ask the participant to explain the three rental-form labels, where to check current attachments and who submits the declaration.
5. Ask them to archive and restore the case, then find the earlier checklist and draft again.

Participants use fictional case inputs, skip document upload and stop at the ANPR handoff. The moderator records the steps and collects feedback. This scenario can also be rehearsed with the repository's browser fixtures. A rehearsal is recorded separately from participant feedback.

## Observation record

| Field | Record |
| --- | --- |
| Session ID, date, build, language and device | Anonymous identifier and session settings |
| Task completed without help | Per-step yes/no and outcome |
| Time and friction | Where the participant stopped, retried or asked for help |
| Handoff comprehension | Can explain what to do in ANPR and where to check current attachment rules |
| Archive and restore | Can find the restored case with progress and PDF intact |
| Critical issue follow-up | Owner, fix reference, and retest evidence |

Pilot completion requires real participant observations and retests of critical issues. No participant sessions are recorded in this guide.

## Agent performance observations

When the reviewed pilot build includes the conversational agent, capture timings from the participant's browser. Use message or clarification submission as the start. Record the elapsed time to the first visible question, proposal, answer or failure, then to verified guidance when it appears. User reading time between submissions belongs to the task completion record. Keep initial submissions and retries distinguishable.

Use anonymous case IDs to link separate service measurements for model calls, tool calls and billed model cost in the billing currency. Include retries and cases without verified guidance in call and cost totals. Record missing usage or unavailable costs explicitly. Use one build and provider configuration per cohort and record language, device and warm or cold start. Retain elapsed times, counters and outcomes with the pilot notes.

Report p50 and p95 with sample counts, verified response coverage and per-case costs. Agree latency and call targets using the measured distribution for successful cases and keep the unsuccessful cases visible alongside it. Set the cost target using the measured spend across attempted cases and the approved pilot budget. Keep targets provisional until the reviewed pilot reproduces them.
