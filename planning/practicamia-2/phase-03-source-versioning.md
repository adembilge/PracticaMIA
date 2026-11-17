# Phase 3.3 — Source identity, versions and case citations

[PracticaMIA 2.0 task 21.3](phase-03-official-sources-and-catalog.md#21-model-procedures-authorities-sources-and-evidence) keeps a source's catalogue identity stable as its content changes and preserves the evidence used in an earlier case step. Authority roles and service channels use this same versioned evidence.

## Registry identity and revision

| Record | What it identifies |
| --- | --- |
| `source_id` | The registered official source. Use the existing `KnowledgeSource.id`. A content change at its registered URL keeps this ID. |
| `source_version_id` | One immutable captured version of the source. Use `KnowledgeSourceVersion.id`. Its `revision` is a sequence within the source. Keep the fetched URL, original captured content, raw SHA-256 and capture provenance with the version. |
| `passage_id` | One exact extracted passage within that version. Current IDs combine the source-version ID and passage ordinal. A repeated ordinal in another revision identifies a different passage. |
| Review decision | Approval or invalidation of the exact version. Current use depends on the active-version pointer, review audit, applicability and snapshot integrity. |

Reuse the [existing snapshot ingestion](../../backend/app/knowledge/snapshots.py). A repeat of the latest captured body and its recorded provenance reuses that version. A changed body at the same registered URL creates the next revision in `pending_review`, with its own passage IDs. A distinct supported capture can also produce a revision when provenance changes. If an active approval exists, ingestion clears the active pointer and records its invalidation in the same transaction. Earlier snapshots, passages, and review history remain available in the registry. If ingestion rejects a capture before saving, the previous state remains intact.

If a later capture matches an older body after an intervening change, compare it with the latest capture and create the next revision when different. Its review is independent of the older approval. An approved version becomes usable through the [existing review workflow](../../docs/KNOWLEDGE_REVIEW_WORKFLOW.md#approval-invariants).

## Citation on a saved case

When a case action or saved answer uses a server-verified passage, store `source_id`, `source_version_id` and `passage_id` together as evidence for that action. A new record requires that the passage belongs to the version, the version belongs to the source, and the passage is currently approved and applicable to the case. Use the reference returned by the server rather than reconstructing it from a title, URL or passage ordinal. An updated action or answer can cite a newer approved passage in a new entry. Preserve the citation on the earlier entry within the case's retention policy.

Case history may identify the source and exact revision used by an earlier entry after verifying case ownership. When that evidence has lost current approval, label its reference as historical and require revalidation before relying on the affected instruction again. If an old passage is unavailable or permission to show it is missing, retain the permitted reference metadata and show that the passage is unavailable. The [approved citation endpoint](../../docs/APPROVED_PASSAGE_SEARCH.md#contract) continues to return `404` for inactive citations, and current guidance still resolves a citation through the approval and scope checks.

## Existing behavior and implementation gap

The current registry already separates source, version and passage IDs. Existing [snapshot tests](../../backend/tests/test_knowledge_snapshots.py) cover unchanged ingestion and preserved older snapshots. [Search tests](../../backend/tests/test_knowledge_search.py) cover invalidation of the old citation and rejection of a stale active pointer. The [saved-case checklist](../../backend/app/cases/workflow_service.py) includes versioned citations in its current-evidence fingerprint. The [encrypted guide history](../../backend/app/preparation/conversation.py) saves answer text, with no structured citation references. Persisting and reading exact references in case history remains an implementation and verification task. Legacy entries without stored references have unknown provenance and must never be linked to a guessed revision.

## Acceptance scenarios

Use a synthetic source at a single registered URL and a fictional owned case.

| Event | Expected result |
| --- | --- |
| Capture the same body with the same provenance twice. | One source, one revision and the same passage references. |
| Save an action using a reviewed passage from revision 1, then change the body at the same registered URL. | The source ID stays stable. Revision 2 starts pending review. Revision 1's stored passage remains intact and its citation is excluded from current guidance. |
| Approve revision 2 and save an updated action citing it. | New guidance can cite revision 2. The first action still references revision 1. The owner can identify the original revision in history. |
| Capture the revision 1 body again after revision 2. | Create revision 3 pending review. The first approval and historical reference remain associated with revision 1. |
| Reopen a legacy entry without a structured citation. | The owner sees unknown provenance on the legacy entry. |
| Attempt to read another user's case history. | The other user's case reference remains inaccessible. |
