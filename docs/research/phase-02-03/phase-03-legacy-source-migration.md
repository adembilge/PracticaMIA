# Phase 3.6 — Carrying Phase 1 source records into the catalogue

[PracticaMIA 2.0 task 21.6](phase-03-official-sources-and-catalog.md#21-model-procedures-authorities-sources-and-evidence) defines how to carry forward the official material identified by the [Phase 1 evidence inventory](phase-01-repo-foundation.md#3-identify-official-documents-and-evidence-to-retain). A record's presence in the old registry, a signed first-route ruleset, or a past approval does not expand its reviewed procedure, jurisdiction, case conditions or date scope.

## Inventory and mapping

Before a data write, produce a read-only, environment-labelled inventory of candidate sources; source versions and active pointers; captured bytes, hashes and passages; reviewer events; signed rule references; and saved-case citation references. For each proposed mapping, record the old and target IDs, official URL, publisher, document type, procedure and jurisdiction, exact version hash, capture method, review event and the scope actually covered by that review. Mark absent or uncertain fields explicitly. A repository file or dated report does not prove the current contents of a hosted database.

Preserve a source ID when it still names the same registered source. A changed body at the same URL remains a different [source version](phase-03-source-versioning.md); keep its historical passage IDs and case references. If an ID or URL collides with a different source, stop that mapping for review rather than overwriting or guessing an alias. Keep original review events and provenance linked to the exact version they concern. Do not mix synthetic fixtures, private case documents, or old case conversations into the shared official-source corpus.

| Legacy record | Target treatment |
| --- | --- |
| Candidate URL or unreviewed snapshot | Preserve as a candidate or pending version. No trusted claim is created. |
| Active approved version with matching original bytes, URL, passage integrity, reviewer event and explicit scope | Carry the existing review evidence only for that exact version and scope. Proposed new authority, channel, date or [claim](phase-03-claim-evidence.md) assignments still need their own review. |
| Approval with unclear procedure, jurisdiction, case conditions, reviewer identity, version or supporting passage | Mark the mapping `needs_review`; withhold it from the new catalogue's trusted results until an authorised human assesses the missing scope and evidence. |
| Revoked, superseded, changed or integrity-failing version | Preserve its permitted history and citations; exclude it from current guidance. A later version starts its own review. |
| Signed first-route rule and saved-case reference | Preserve the narrow reviewed Milan scope and exact citation or signature relationship. Do not convert it into an Italy-wide rule or a fresh source approval. |

The [8 November first-route record](../../docs/MILAN_FIRST_ROUTE_OWNER_REVIEW_ACTIVATION_2026_11_08.md#decision-scope-and-limitations) documents a limited owner-reviewed ruleset and distinct source approvals. It is dated evidence, not a current database audit or permission to broaden that route. Current trusted use still requires the [registry checks](../../docs/OFFICIAL_SOURCE_REGISTRY.md#trust-model), including active revision, audit and snapshot integrity. An old approval with clear scope may remain usable within the existing registry only while those checks pass. Copying its data into a new catalogue must not manufacture a new approval event or set a target version to approved by direct write; use the authenticated human [review workflow](../../docs/KNOWLEDGE_REVIEW_WORKFLOW.md#approval-invariants) for any new activation.

## Migration rehearsal and release gate

1. Generate a dry-run mapping and exception report, including record counts, ID collisions, missing snapshots, invalid hashes, unclear approval scopes and affected case citations. Keep personal case content out of the report.
2. Rehearse an additive import on a disposable, migration-compatible PostgreSQL branch with synthetic case references. Preserve the existing Alembic history and source/version/passage relationships. Do not touch production or change reviewer permissions.
3. Re-run the import to prove idempotence, then compare record counts, hashes, audit links and historical citation IDs. Check that candidate and held records are absent from trusted search and that an old case reference is not silently redirected to a new passage.
4. Submit exceptions to an authorised reviewer with the exact source version, scope question and supporting material. Record the decision; no inferred or synthetic approval clears a hold. Roll back the new catalogue route if verification fails, leaving the legacy records intact for recovery.

This is a migration contract, not an executed data inventory or migration. The existing [candidate registration](../../backend/app/knowledge/catalog.py) inserts missing metadata without overwriting approvals, and approved retrieval already filters by source status, version, jurisdiction and procedure. No general Phase 1-to-2.0 mapping or exception review has been implemented or run.

## Acceptance scenarios

Use synthetic source records, reviewer events and case citations in an isolated database.

| Scenario | Expected result |
| --- | --- |
| A candidate has a URL but no captured version. | It remains a candidate and contributes no trusted passage. |
| An approved Milan version has intact bytes, audit and explicit scope. | Its original review remains traceable only to that scope; new catalogue claims remain pending. |
| A version is marked approved but its audit or applicable scope is missing. | The mapping needs review and cannot enter trusted 2.0 retrieval. |
| Two old IDs or URLs map to different target sources. | Report the collision without overwriting either record or changing old citations. |
| A newer capture exists after an approved version. | The older version remains historical; it is not revived as current by migration. |
| A fictional saved case cites an old passage. | Preserve its exact version-scoped reference under case access controls; current guidance rechecks active evidence. |
| The import is run twice. | The second run adds no duplicate source, version, passage, audit or mapping records. |
