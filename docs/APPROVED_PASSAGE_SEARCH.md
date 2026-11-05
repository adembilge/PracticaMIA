# Approved passage lexical retrieval — milestone 50.4 foundation

**Status:** Feature PR. Backend-only search and citation resolution. No AI-generated legal guidance, embeddings or production knowledge rollout.

## Contract

Search results come **only** from active, human-reviewed official-source snapshots. The caller must supply a *known, verified* jurisdiction, procedure and language; the server never guesses them from an LLM query. When evidence is missing, the API returns `insufficient_evidence` and an empty list rather than inventing a citation.

Authenticated API (feature-flagged):

```http
GET /api/v1/knowledge/search?query=residenza&jurisdiction=IT-MI-MILANO&procedure_id=milan_residence_change&language=it&limit=5
Authorization: Bearer <access_token>
```

Response fields: `status` (`evidence_found` or `insufficient_evidence`), `normalized_query`, required scope filters and `evidence`. Every evidence entry includes:

- `citation_id` and `passage_id` (same stable, version-scoped identifier)
- `source_id`, `source_version_id`, `source_revision`
- institution, title, official URL, jurisdiction, procedure and language
- section path, exact extracted passage text and passage SHA-256
- source SHA-256, retrieval timestamp and human review timestamp

Citation resolution:

```http
GET /api/v1/knowledge/passages/{citation_id}?jurisdiction=IT-MI-MILANO&procedure_id=milan_residence_change&language=it
Authorization: Bearer <access_token>
```

Resolution returns the same evidence entry only while that version remains active and valid; otherwise `404`. This is deliberate: a revoked, changed or superseded source must not be represented as current evidence.

Normal signed-in users may read approved public evidence. Only separately allowlisted reviewers can approve or revoke sources; the search API does not grant review permissions.

## Trust gates

A candidate passage must pass **all** of these checks before it is returned:

1. Database query filters by `jurisdiction`, `procedure_id`, and `language`, all supplied explicitly, before ranking.
2. Source status is `approved` and `active_version_id` equals the passage's version.
3. Version status is `approved`, with a reviewer identity and review date.
4. That version is still the **latest** source revision.
5. The latest matching review audit event confirms approval of this exact content hash and reviewer.
6. Stored snapshot URL matches its registered official URL; raw-byte hash and extraction version are verified.
7. Every stored passage, offset, heading and SHA-256 matches a fresh extraction from the original HTML.

The existing `GET /api/v1/knowledge/sources` metadata catalog now applies the same review-history/integrity gate, preventing an unlogged status update from being treated as approved evidence. Unreviewed, withdrawn, tampered, superseded or out-of-scope data never enters the response.

## Lexical ranking

Alembic migration `20261105_0006` adds a PostgreSQL **GIN expression index**:

```sql
CREATE INDEX ix_knowledge_passages_fts_simple
ON knowledge_source_passages
USING GIN (to_tsvector('simple'::regconfig, content));
```

The PostgreSQL search path uses parameterized `plainto_tsquery('simple', query)`, the indexed `@@` predicate and `ts_rank_cd` ordering. The `simple` dictionary preserves basic lexemes across Italian and English, but does not perform language-specific stemming or semantic matching. Search syntax is normalized to plain words: it cannot introduce SQL operators or arbitrary retrieval filters.

Query size is limited to 180 characters and 12 words. Results are limited to 1–10 passages, with a bounded 200-candidate integrity verification phase.

A bounded, exact-token **SQLite fallback** exists solely for isolated unit tests. PostgreSQL is required for the real indexed search; CI includes a separate genuine PostgreSQL integration smoke test.

### Limitations

- **No relevance claim beyond lexical matching.** Synonyms, Italian morphology, multiword semantics and multilingual paraphrases are future retrieval-quality work.
- The GIN index includes candidate text internally; the application **always** filters approval and jurisdiction before presenting any result.
- The result is evidence, **not** an eligibility verdict, mandatory document list or approved legal interpretation.
- Search does not independently check whether a real government page is updated today. Review timestamps are exposed and ingestion/change detection plus revocation are required operational controls.
- Review of actual municipal source snapshots is still a human action. Tests use **synthetic examples only**, not copied official legal text.
- This task does not perform crawling, source imports, bulk review, embeddings, pgvector, LLM prompting or ChatGPT-style chat.

## Deployment and acceptance

Production Neon is currently at `20261104_0002`, and existing knowledge flags remain disabled. **Merging this code is not permission to migrate or enable the knowledge API.**

1. Review the PR and CI results.
2. Confirm Neon backup/restore, create a disposable branch and test migrations `0003` through `0006`.
3. Register permitted official source candidates, ingest faithful snapshots, and individually approve them through the authenticated reviewer workflow.
4. Only then consider enabling `ENABLE_KNOWLEDGE_CATALOG_API=1` and `ENABLE_KNOWLEDGE_SEARCH_API=1` in a controlled environment.
5. Test `401`, `insufficient_evidence`, scope mismatch, citation resolution, revocation and source-change invalidation.
6. Enable no user-facing AI guidance until source provenance and relevance fixtures have been reviewed.

**Next:** Retrieval evaluation fixtures (MRR, Recall@K, citation correctness), embeddings/pgvector hybrid fusion, explicit freshness policies and deterministic administrative rules, followed by a bounded LangGraph agent.
