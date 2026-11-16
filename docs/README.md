# Project documentation

Start with the [project overview](../README.md). The [complete specification](../PracticaMIA_Complete_Project_Specification.md) defines product intent and acceptance criteria. [Progress and blockers](PROGRESS.md) records which claims have evidence, in which environment, and on which revision.

## Case and document workflows

| Topic | Reference |
| --- | --- |
| Saved case, typed intake, and review marks | [Case workflow](UNIFIED_CASE_WORKFLOW.md) · [Structured intake](STRUCTURED_CASE_INTAKE.md) |
| Signed first-route rules and output | [Checklist](REVIEWED_CASE_CHECKLIST.md) · [Preparation PDF](CASE_PREPARATION_EXPORT.md) |
| Optional AI explanation | [Case-aware AI guidance](CASE_AWARE_AI_GUIDANCE.md) |
| Restricted private document handling | [Vault release controls](PRIVATE_DOCUMENT_VAULT_RELEASE.md) · [Document intelligence](PRIVATE_DOCUMENT_INTELLIGENCE.md) |

## Knowledge and provenance

| Topic | Reference |
| --- | --- |
| Candidates and acquisition | [Source registry](OFFICIAL_SOURCE_REGISTRY.md) · [Source intake](OFFICIAL_SOURCE_INTAKE.md) |
| Capturing evidence | [HTML snapshots](CONTROLLED_SOURCE_SNAPSHOTS.md) · [PDF ingestion](PDF_SOURCE_INGESTION.md) · [Browser captures](BROWSER_CAPTURE_EVIDENCE.md) |
| Authenticated review | [Review workflow](KNOWLEDGE_REVIEW_WORKFLOW.md) · [Mobile queue](MOBILE_BROWSER_SOURCE_REVIEW.md) |
| Approved-only retrieval | [Lexical passage search](APPROVED_PASSAGE_SEARCH.md) · [Embedding indexing](APPROVED_EMBEDDING_INDEXING.md) · [Retrieval evaluation](RETRIEVAL_EVALUATION.md) |

## Development and release

- [Development and GitHub review workflow](DEVELOPMENT_WORKFLOW.md)
- [Backend setup](../backend/README.md) and [frontend setup](../frontend/README.md)
- [Auth0 integration](AUTHENTICATION_INTEGRATION.md)
- [Vercel and Neon deployment](VERCEL_NEON_DEPLOYMENT.md)
- [Browser acceptance and hosted observations](ACCEPTANCE_TESTING.md)
- [Opt-in authenticated Preview runbook](AUTHENTICATED_PREVIEW_E2E_RUNBOOK.md)
- [Milan pilot guide](MILAN_PILOT.md)

## Planning and decisions

- [Master plan](MASTER_PLAN.md), [task registry](TASKS.yaml), [progress and blockers](PROGRESS.md), and [decision log](DECISIONS.md)
- [Repository agent instructions](../AGENTS.md)

## Dated evidence

The scope, source state and observations below refer to the dates and environments recorded in each document. Check active, reviewed versions for current use.

| Date | Record |
| --- | --- |
| 5 Nov 2026 | [Milan source discovery](MILAN_OFFICIAL_SOURCE_ACQUISITION.md) · [HTTP access audit](OFFICIAL_HTML_ACCESS_AUDIT_2026_11_05.md) · [Browser observations](research/BROWSER_OBSERVED_MILANO_RESIDENCE_2026_11_05.md) · [Unapproved Allegato A import](ALLEGATO_A_STAGING_INGESTION.md) |
| 6 Nov 2026 | [Independent system audit](audits/INDEPENDENT_SYSTEM_AUDIT_2026_11_06.md) |
| 7 Nov 2026 | [ANPR uploaded-guide comparison](ANPR_PUBLIC_GUIDE_UPLOAD_REVIEW_2026_11_07.md) |
| 8 Nov 2026 | [Owner review and first-route activation](MILAN_FIRST_ROUTE_OWNER_REVIEW_ACTIVATION_2026_11_08.md) |
