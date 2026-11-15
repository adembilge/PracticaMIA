# Approved-only pgvector embeddings — staging workflow

The purpose is to index only public municipal passages whose exact
source versions have already been reviewed and approved. The indexer
**does not approve sources** and does not process personal case records.

The dry-run queries the selected staging branch for approved, unindexed passages. For dated source approval evidence, see [first-route activation](MILAN_FIRST_ROUTE_OWNER_REVIEW_ACTIVATION_2026_11_08.md). Approval requires a verified Auth0 reviewer on the server allowlist.

## Dry-run with zero provider calls

From `backend/`, after securely configuring `DATABASE_URL` for the
isolated Neon staging branch. Use the repository’s migration head or another revision explicitly accepted by [the staging guard](../backend/app/knowledge/staging_guard.py).


```sh
export PRACTICAMIA_KNOWLEDGE_TARGET=staging
python -m app.knowledge.approved_embedding_index
```

The command outputs only approved passage IDs, content hashes and counts.
It does not print the full text, write to the database or contact a model.
A zero result means there are no eligible unindexed passages in that run. The fixed model is `text-embedding-3-small` with 1,536 dimensions.

## Explicit indexing after legitimate review approval

**Only after** legal-source applicability, provider privacy, budget and
quality evaluations are completed, the operator may provide the API key
through a secure environment secret store and run:

```sh
export PRACTICAMIA_KNOWLEDGE_TARGET=staging
# DATABASE_URL = verified staging; OPENAI_API_KEY = operator-managed secret
python -m app.knowledge.approved_embedding_index \
  --apply --confirm-public-source-transfer --max-passages 100
```

This is an explicit external provider transfer of **approved public text
only**, not user questions, Auth0 claims, case records, uploaded documents,
or any other private data. Maximum 100 passages per operation. No key or
provider call is required for the dry-run.

## Technical safeguards

- PostgreSQL-only staging schema guard and explicit
  `PRACTICAMIA_KNOWLEDGE_TARGET=staging`; never target production.
- Before any transfer, the plan selects latest, active, individually
  approved versions, verifies the most recent review audit event, original
  text/capture hashes and all passage offsets.
- Existing vectors for the same approved passage hash and model are skipped
  (idempotent).
- The provider is called **once** for the bounded reviewed passage batch.
- After the provider responds, every passage is rechecked for current
  approval and unchanged content. All vector writes run in one transaction;
  a revocation or changed hash aborts the batch. Provider errors cannot
  create partial database records.
- Vectors from revoked sources may remain stored for bookkeeping but are
  excluded by the approved-only search gates immediately; model retrieval
  requires the source's current active reviewer-approved version.
- No automatic source approval, scheduled index refresh, chat-model
  activation or production guidance release is performed.

## Tests

- Unit tests use a fake embedding provider and reject missing, zero,
  non-finite and wrong-dimensional vectors.
- Disposable PostgreSQL pgvector integration tests prove pending sources
  cannot be indexed; reviewer-approved synthetic sources can be indexed;
  repeat plans are empty; revoked sources become unsearchable; and
  revocation during provider work causes the write to fail closed.
- All tests use invented text, synthetic reviewer events and rolled-back
  databases. Passing tests does not constitute independent government
  document verification.

## Remaining milestones

Continue source-by-source approval for new material. The [hybrid retrieval helper](../backend/app/knowledge/vector_search.py) accepts caller-provided query vectors. The current [Preview assistant endpoint](../backend/app/knowledge/assistant_router.py) uses approved topic passages or lexical retrieval and does not generate a query embedding. Benchmark the vector path with labeled bilingual examples and review any external query transfer before adding it to the endpoint. See [retrieval evaluation](RETRIEVAL_EVALUATION.md).
