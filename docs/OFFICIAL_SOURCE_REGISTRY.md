# Official-source registry and evidence lifecycle

PracticaMIA maintains a versioned registry of official administrative sources. A registered URL is a **candidate**, not proof that a document has been acquired, reviewed, remains current, or applies to a particular case.

## Components

- `backend/app/knowledge/candidate_sources.json`: version-controlled candidate source metadata.
- `catalog.py` and `model.py`: registry models and candidate registration.
- `snapshots.py`, `html_extraction.py`, and `pdf_extraction.py`: controlled original-byte snapshots and structured passage extraction.
- `review_service.py` and `review_router.py`: reviewer-controlled version approvals, revocations, and associated audit records.
- `search.py`, `vector_search.py`, and `search_router.py`: approved-only lexical/hybrid retrieval and passage resolution.
- `approved_embedding_index.py`: bounded indexing of reviewed public passages, with explicit transfer and environment safeguards.

Alembic migrations evolve the registry, content snapshots, review events, PostgreSQL full-text search, and pgvector storage. **Keep every migration in sequence**; deletion or squashing could break existing databases.

## Trust model

A source contributes to trusted retrieval only while its active version passes all required checks: correct jurisdiction and procedure, current approval, independent reviewer audit, matching official URL and content digest, valid passage provenance, and absence of revocation or supersession. The application fails closed when evidence is absent or outdated.

The versioned source registry is separate from the **deterministic administrative ruleset**. An approved source passage by itself does not grant an AI model permission to decide legal eligibility, required documents, fees, deadlines, or government submission status.

A reviewer decision is a privileged operation; it is never inferred from a user prompt, test fixture, or direct database status change. For the recorded scope of the first reviewed Milan ruleset, see [the owner review and activation record](MILAN_FIRST_ROUTE_OWNER_REVIEW_ACTIVATION_2026_11_08.md). The historical [Milan source inventory](MILAN_OFFICIAL_SOURCE_ACQUISITION.md) is not a current approval or deployment report.

## API and activation

Authenticated clients can read active approved source metadata through `GET /api/v1/knowledge/sources` when the case and catalog APIs are configured. Search and citation resolution have separate gates. Reviewer-only operations require a distinct allowlist and enabled review API. Consult `backend/app/config.py` and `backend/app/main.py` for the actual environment flags and startup validation; do not assume the repository's code is activated in any particular deployment.

An isolated development database can be migrated and candidate metadata inspected using:

```bash
cd backend
alembic -c alembic.ini upgrade head
python -m app.knowledge.seed_candidates
```

Seeding candidates with `--apply` is an explicit write; use it only on an authorized database and confirm the exact target first. Do not migrate production, approve a source, or enable sensitive routes merely to make a test pass.

## Related guidance

- [Controlled source snapshots](CONTROLLED_SOURCE_SNAPSHOTS.md)
- [Source acquisition runbook](OFFICIAL_SOURCE_INTAKE.md)
- [Human review and approval](KNOWLEDGE_REVIEW_WORKFLOW.md)
- [Approved passage retrieval](APPROVED_PASSAGE_SEARCH.md)
- [Embedding indexing](APPROVED_EMBEDDING_INDEXING.md)
- [Retrieval evaluation](RETRIEVAL_EVALUATION.md)

PracticaMIA is independent of government authorities. Review status and provenance are engineering controls, not certification that any administrative decision will be accepted. 
