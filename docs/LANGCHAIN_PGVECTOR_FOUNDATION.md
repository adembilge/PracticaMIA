# LangChain + pgvector RAG foundation (development milestone)

**Status:** PR #18, backend-only development foundation. No live LLM
credentials, public answer endpoint, automatic embeddings, official-source
approval or production database migration are included. This is not yet a
user-facing RAG system.

## Architecture

1. **Human-reviewed source ingestion:** Existing snapshot importer preserves
   original HTML/PDF bytes, exact version hash, passage hashes and review
   history. Approved-only evidence is a strict input requirement.
2. **PostgreSQL + pgvector:** Migration `20261105_0007` adds the `vector`
   extension and a separate `knowledge_passage_embeddings` table. A
   1,536-dimensional embedding is bound to the exact passage ID, source
   version ID, text SHA-256 and embedding-model ID. HNSW indexes cosine
   distance; the existing GIN full-text index is retained.
3. **Hybrid retrieval:** PostgreSQL ranks semantic candidates by cosine
   distance; existing lexical search ranks keyword matches. Results are
   fused using reciprocal rank fusion (RRF, k=60), deduplicated and returned
   with original passage citations.
4. **Revalidation:** Both rankings are restricted to scoped, active,
   approved-version metadata. Every semantic result must independently
   pass the existing reviewer audit, original-source byte hash, extraction,
   passage-offset and source-version verification checks. Revoked or
   changed sources cannot be returned, even with stale vectors.
5. **LangChain:** `rag_chain.answer_from_passages` composes an evidence-only
   prompt using `langchain-core` and invokes an explicitly provided chat
   model. When no approved passages exist it returns
   `insufficient_evidence` **without calling an LLM**.

There is **no LangGraph orchestration**. This is deliberately a two-step RAG
foundation rather than a tool-using autonomous agent.

## Operator API (not exposed as HTTP endpoints)

- `index_approved_passage_vector(db, citation_id=..., model_id=..., embedding=..., jurisdiction=..., procedure_id=..., language=...)`
  upserts a vector only if its underlying passage is trusted now.
- `search_approved_semantic(db, query_embedding=..., model_id=..., jurisdiction=..., procedure_id=..., language=...)`
  performs scoped semantic retrieval and re-verifies citations.
- `search_approved_hybrid(db, query=..., query_embedding=..., model_id=..., jurisdiction=..., procedure_id=..., language=...)`
  fuses that result with existing lexical evidence. If the query embedding
  and model ID are omitted, it stays lexical-only.
- `answer_reviewed_question(db, question=..., jurisdiction=..., procedure_id=..., language=..., chat_model=..., query_embedding=..., model_id=...)` is the combined two-step service entry point: approved retrieval and automatic abstention before any generation.
- `answer_from_passages(question=..., passages=..., chat_model=...)`
  creates a LangChain evidence prompt and calls a supplied model; it does
  not itself fetch or verify documents. Always call it with trusted results
  from the approved-only retrieval functions.

The 1,536 dimensions are an explicit schema choice; an embedding provider
must output **exactly** 1,536 finite values. Changing provider or model
requires a separate quality comparison and reindexing plan. `model_id`
prevents accidental cross-model comparisons; all vectors in a query use the
same selected model. No API key or provider is configured by this milestone.

### Example (offline concept, no network)

```python
with session_factory() as db:
    passages = search_approved_hybrid(
        db, query="synthetic sample", jurisdiction="IT-MI-MILANO",
        procedure_id="milan_residence_change", language="it",
        query_embedding=synthetic_vector, model_id="ci-synthetic-1536",
    )
    # Only trusted passages reach the model; none -> deterministic abstention.
    answer = answer_from_passages(
        question="synthetic sample", passages=passages,
        chat_model=local_test_chat_runnable,
    )
```

The synthetic vectors and fake model are test fixtures, not government
guidance or production-quality embeddings.

## Safety and release gates

- Do **not** expose a route until trusted authenticated case scope is
  derived server-side; never let the LLM choose jurisdiction, procedure,
  review state or a user-scoped document collection.
- Do **not** index pending-review or historically outdated official pages
  solely because they exist in the database. The uploaded 2013 **Allegato A**
  remains **pending_review** and excluded.
- Do **not** automatically send government source text or user questions to
  a third-party model before a provider/privacy decision and documented
  approval. No private user documents belong in the public evidence table.
- A model may still hallucinate or ignore evidence; supplied citation
  metadata does not prove every generated sentence is correct. Validate
  claims, abstention, multilingual quality, and citations in a separate
  evidence-grounded evaluation before user-facing release.
- Keep production features disabled. Implement rate limiting, prompt
  injection tests, cost control, evidence-freshness policy and failure
  handling before enabling any real LLM.
- No actual embeddings have been generated for the existing approved
  knowledge base, which is still empty.

## Verified isolated staging rollout (5 November 2026)

After PR #18 was merged, the PostgreSQL-only migration `20261105_0007`
was applied transactionally to Neon staging
`staging-knowledge-0003-0006-2026-11-05` (the existing branch name is
unchanged). Direct read-only verification confirmed pgvector **0.8.0**,
`ix_knowledge_embedding_cosine`, one `pending_review` original PDF
version with three extracted passages, **zero approved versions** and
**zero embeddings**. Production remains on `20261104_0002`. A subsequent audited change applied migration `20261105_0008` to the same isolated staging branch for a shared, pseudonymous assistant model-call quota; no source approvals or embeddings were added.

## Validation

GitHub Actions uses a disposable `pgvector/pgvector:pg17` PostgreSQL
service, runs Alembic to the latest revision and tests semantic retrieval
with synthetic 1,536-dimensional vectors. Unit tests use an offline
LangChain Runnable mock. These tests exercise correctness and security
invariants, **not** retrieval accuracy on real Milan government documents.

## Rollout sequence

1. Merge only after backend/frontend CI and Vercel previews pass.
2. Migration `20261105_0007` has been applied to **isolated staging**. Do not
   update production schema in this release.
3. Obtain and independently approve current government evidence; maintain
   exclusion for the historic 2013 PDF.
4. Choose an embedding provider and versioned model, record its privacy
   implications and cost; run a controlled, operator-invoked indexing pass
   on **approved** passages only.
5. Benchmark multilingual Recall@K, MRR, source/version citation integrity,
   abstention and prompt injection. Only then design an authenticated
   FastAPI RAG endpoint behind a disabled-by-default feature flag.
