# Retrieval Evaluation — Synthetic Lexical Baseline

**Milestone:** Stage 7 retrieval quality preparation (tasks 50–51). This is
**not** semantic RAG, not a completed official-source audit, and not a verified
administrative-rules evaluation.

## Implemented

- `backend/app/knowledge/retrieval_eval.py` scores exact ranked citation IDs.
- `evals/fixtures/knowledge_retrieval_synthetic.json` is an openly labeled,
  invented two-page Italian corpus with three positive queries and one negative.
  Its source IDs are existing candidate IDs, but the HTML is **not** from a
  government website. It is used only inside disposable tests.
- `backend/tests/test_retrieval_eval_metrics.py` independently validates
  Recall@K, MRR, negative-query abstention, no-hit behavior and invalid inputs.
- `backend/tests/test_postgres_retrieval_eval.py` exercises the real GIN-indexed
  PostgreSQL search and approval audit. It ingests and approves synthetic
  snapshots inside a disposable database transaction, verifies each result's
  exact resolvable citation, and rolls back everything afterward.
- Backend CI runs this integration benchmark before the existing search smoke
  test. No production databases, live government pages, paid APIs or LLM calls.

## Metrics and interpretation

For positive query `q`, with independently labeled relevant passage IDs
`G(q)` and a ranked top-K result `R_K(q)`:

- **Recall@K** = `|G(q) ∩ R_K(q)| / |G(q)|`.
- **Reciprocal rank** = `1 / rank(first relevant passage)`, or zero if none.
- **MRR@K** = mean reciprocal rank over positive queries.
- **Negative abstention rate** = share of negative queries with zero results.

Macro-average Recall@K over positive queries; do not mix negative questions
into the denominator. Duplicated citation IDs and more than K results fail
metric validation. Citation resolution is an independent integration assertion.

The synthetic fixture expects Recall@5 = **1.0**, MRR@5 = **1.0**, and negative
abstention = **1.0** as a regression test, **not measured real-world quality**.
A passing test proves that basic exact-term ranking, authorization-independent
approval state, scope constraints and citation resolution continue to work on
this tiny synthetic corpus. It says nothing about Italian legal correctness,
multilingual paraphrases, large-corpus ranking, actual source freshness or
agent decision quality.

## Reproduce

From `backend/`:

```bash
python -m pip install -e '.[dev]'
python -m pytest -q tests/test_retrieval_eval_metrics.py
```

On an **isolated, migrated** PostgreSQL database only, set
`DATABASE_URL` to that disposable database, and run:

```bash
RUN_POSTGRES_SMOKE=1 python -m pytest -q tests/test_postgres_retrieval_eval.py
```

Do not point this benchmark at production or staging Neon. CI already runs the
PostgreSQL benchmark after upgrading its own disposable database to Alembic
head. The test creates a synthetic approval event solely for testing; it does
not approve any real source.

## Next quality gates before user-facing administrative guidance

1. Acquire authentic, permitted source snapshots and have a human reviewer
   verify originals and extraction. HTTP 403 or search snippets are **not**
   sufficient evidence.
2. Create a human-labeled corpus with source versions, exact relevant passages,
   query paraphrases, no-answer cases, and cases across jurisdictions.
3. Separate development and holdout queries; assess Recall@K, MRR, citation
   validity, coverage, source-change invalidation and abstention. Define
   meaningful thresholds only after establishing a representative baseline.
4. Implement and compare semantic embeddings plus pgvector hybrid fusion
   against this lexical baseline, without weakening source approval gates.
5. Build deterministic verified administrative rules before allowing an agent
   to derive personalized requirements.

**Never publish a synthetic test score as a real user, RAG, or legal-accuracy
metric.**
