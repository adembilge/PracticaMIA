# Canonical roadmap evidence reconciliation

**17 November 2026.** This reviews the completion criterion of each of the 94 parent tasks in [TASKS.yaml](TASKS.yaml) against checked-in artifacts and the dated observations in [PROGRESS.md](PROGRESS.md). `P` means relevant evidence exists but does not establish the full criterion. `B` means the criterion is blocked by missing evidence, a required human decision, or an unperformed live check. Neither mark means the task is completed. The source links below identify what was examined; a code path or a dated test is not a fresh production check. All task statuses remain `pending` until their dependencies, acceptance evidence and human gates are individually satisfied.

## 1. Product discovery and definition

| Task | Review | Evidence examined | Missing for completion |
| --- | --- | --- | --- |
| 1 | B | [Specification](../PracticaMIA_Complete_Project_Specification.md), [pilot scope](MILAN_PILOT.md) | Explicit review and approval of the product vision. |
| 2 | P | [Phase 2 research plan](../planning/practicamia-2/phase-02-user-research-and-scope.md) | Sourced participant findings and unresolved hypotheses recorded together. |
| 3 | P | [Specification §2](../PracticaMIA_Complete_Project_Specification.md#2-problem-and-opportunity) | Current, sourced competitor matrix and differentiation review. |
| 4 | P | [Milan scope](REVIEWED_CASE_CHECKLIST.md), [owner decision](DECISIONS.md#d-004--align-the-scope-questions-with-the-signed-milan-route-14-november-2026) | Approval of the complete in/out matrix across proposed cases. |
| 5 | P | [Synthetic acceptance scenarios](ACCEPTANCE_TESTING.md) | Reference case collection covering the whole requested scenario matrix. |
| 6 | B | [Specification](../PracticaMIA_Complete_Project_Specification.md) | Approved `PRODUCT.md` and stable requirement ID review. |

## 2. Government procedure research

| Task | Review | Evidence examined | Missing for completion |
| --- | --- | --- | --- |
| 7 | P | [Milan source inventory](MILAN_OFFICIAL_SOURCE_ACQUISITION.md) | Auditable inventory covering every intended pilot procedure. |
| 8 | P | [Reviewed Milan checklist](REVIEWED_CASE_CHECKLIST.md), [Phase 2 procedure map](../planning/practicamia-2/phase-02-administrative-domains.md) | Reviewed step/branch/handoff map for all approved pilot cases. |
| 9 | P | [Signed Milan rules](../backend/app/rules/catalog.json) | Versioned eligibility table for the whole pilot scope. |
| 10 | P | [Milan source inventory](MILAN_OFFICIAL_SOURCE_ACQUISITION.md) | Complete, source-linked conditional document catalogue. |
| 11 | B | [Milan source inventory](MILAN_OFFICIAL_SOURCE_ACQUISITION.md) | Reviewed deadlines and obligations registry; do not infer dates. |
| 12 | P | [Service-channel design](../planning/practicamia-2/phase-03-service-channels.md) | Verified handoff for each supported scenario and current channel. |
| 13 | P | [Administrative domain research](../planning/practicamia-2/phase-02-administrative-domains.md) | Reviewed dependency map for related procedures. |
| 14 | B | [Source review record](MILAN_MVP_ACCEPTANCE_2026_11_15.md) | Full evidence dossier and specific human approval or explicit source blocker per case. |

## 3. UX and product design

| Task | Review | Evidence examined | Missing for completion |
| --- | --- | --- | --- |
| 15 | P | [Case workflow](UNIFIED_CASE_WORKFLOW.md) | Reviewed journey diagrams for supported branches and interruptions. |
| 16 | P | [Intake schema](STRUCTURED_CASE_INTAKE.md) | Review of the complete collection schema across pilot cases. |
| 17 | P | [Agent guidance](CASE_AWARE_AI_GUIDANCE.md) | Reviewed conversation patterns and negative examples across target languages. |
| 18 | P | [Frontend routes](../frontend/src/app) | Reviewed key-screen and route design, including accessibility review. |
| 19 | P | [Workflow UI](../frontend/src/components/CaseWorkspace.tsx) | Explicit recovery flows for major errors and interruptions. |
| 20 | B | [Frontend guide](../frontend/README.md) | Owner-approved design system and accessibility baseline. |

## 4. System architecture

| Task | Review | Evidence examined | Missing for completion |
| --- | --- | --- | --- |
| 21 | P | [Specification §18](../PracticaMIA_Complete_Project_Specification.md#18-data-architecture-and-proposed-entities) | Reviewed component and trust-boundary diagrams with human approval. |
| 22 | P | [Models](../backend/app/cases/model.py), [migrations](../backend/migrations/versions) | Reviewed cross-domain schema and indexing plan. |
| 23 | P | [Workflow service](../backend/app/cases/workflow_service.py) | Complete, testable case and agent state machines. |
| 24 | P | [Rule engine](../backend/app/rules/engine.py) | Rules schema for all approved fixtures and human approval. |
| 25 | P | [Private document design](PRIVATE_DOCUMENT_INTELLIGENCE.md) | Reviewed end-to-end document pipeline and human approval. |
| 26 | B | [Vault release checklist](PRIVATE_DOCUMENT_VAULT_RELEASE.md), [audit](audits/INDEPENDENT_SYSTEM_AUDIT_2026_11_06.md) | Security/privacy design review, provider/privacy and operational sign-offs. |
| 27 | P | [API specification](../PracticaMIA_Complete_Project_Specification.md#19-api-contracts-and-event-flows) | Approved current interface contracts rather than proposed endpoints. |

## 5. Codex and development environment

| Task | Review | Evidence examined | Missing for completion |
| --- | --- | --- | --- |
| 28 | P | [Agent instructions](../AGENTS.md) | Recorded review of persistent instructions against current workflow. |
| 29 | P | [Task registry](TASKS.yaml), [validator](../scripts/validate_roadmap.py) | Validator passes; acceptance review of task ordering and dependencies remains. |
| 30 | P | [Progress](PROGRESS.md), [decisions](DECISIONS.md) | Fresh-session reconstruction demonstrated and recorded. |
| 31 | P | [Backend](../backend/app), [frontend](../frontend/src), [CI](../.github/workflows) | Repository integrity from a clean checkout. |
| 32 | P | [Backend dependencies](../backend/pyproject.toml), [frontend lockfile](../frontend/package-lock.json) | Reproducible clean install and required DB extension check. |
| 33 | P | [Local compose](../backend/compose.yaml), [runbooks](VERCEL_NEON_DEPLOYMENT.md) | Clean checkout boots both services with documented setup. |
| 34 | P | [CI workflows](../.github/workflows), [acceptance record](ACCEPTANCE_TESTING.md) | Confirm mandatory failures are detected and reported on current revision. |
| 35 | B | [Development workflow](DEVELOPMENT_WORKFLOW.md) | Recorded reproducible sample iteration from a fresh session. |

## 6. Backend foundation

| Task | Review | Evidence examined | Missing for completion |
| --- | --- | --- | --- |
| 36 | P | [FastAPI app](../backend/app/main.py), [backend CI](../.github/workflows/backend-ci.yml) | Current clean API smoke and unit evidence linked to exact SHA. |
| 37 | P | [Migrations](../backend/migrations/versions), [PostgreSQL smoke](../backend/tests/test_postgres_smoke.py) | Fresh migration and integrity run on disposable DB for current revision. |
| 38 | P | [Auth integration](AUTHENTICATION_INTEGRATION.md), [auth tokens](../backend/app/auth/tokens.py) | Complete positive and negative auth tests, including live paths. |
| 39 | P | [Case API tests](../backend/tests/test_cases_api.py), [manual isolation](ACCEPTANCE_TESTING.md) | Cross-user write, upload and reviewer isolation in intended environment. |
| 40 | B | [Account page](../frontend/src/app/account/page.tsx) | Profile CRUD and validation contract/tests. |
| 41 | P | [Case workflow](UNIFIED_CASE_WORKFLOW.md), [workflow tests](../backend/tests/test_case_workflow.py) | Complete lifecycle and invalid-transition acceptance. |
| 42 | B | [Vault checklist](PRIVATE_DOCUMENT_VAULT_RELEASE.md), [private document tests](../backend/tests/test_private_documents.py) | Intended scanner, hosted isolation and operational controls. |
| 43 | P | [Backend CI](../.github/workflows/backend-ci.yml), [tests](../backend/tests) | Current full integration run with its environment and failures recorded. |

## 7. Government knowledge engine

| Task | Review | Evidence examined | Missing for completion |
| --- | --- | --- | --- |
| 44 | P | [Registry](OFFICIAL_SOURCE_REGISTRY.md), [review service](../backend/app/knowledge/review_service.py) | Full version/permission matrix and live reviewer validation. |
| 45 | P | [Ingestion](../backend/app/knowledge/ingest_source.py), [approved index](APPROVED_EMBEDDING_INDEXING.md) | Each of six subtask criteria and exact-version trace checked together. |
| 46 | B | [Claim-evidence design](../planning/practicamia-2/phase-03-claim-evidence.md), [rules catalogue](../backend/app/rules/catalog.json) | General claim records and human review of all activated rules. |
| 47 | P | [Rule tests](../backend/tests/test_signed_milan_rules_active_v1.py) | Golden set for every approved ruleset and version. |
| 48 | P | [Scope logic](../backend/app/cases/scope.py), [scope tests](../backend/tests/test_scope.py) | Routing fixtures across intended procedures and jurisdictions. |
| 49 | P | [Checklist service](../backend/app/cases/checklist_service.py), [tests](../backend/tests/test_case_checklist.py) | Golden cases across all supported procedure branches. |
| 50 | P | [Approved passage search](APPROVED_PASSAGE_SEARCH.md), [retrieval tests](../backend/tests/test_knowledge_search.py) | Six retrieval subtask criteria plus current jurisdiction/version citation gate. |
| 51 | P | [Retrieval evaluation](RETRIEVAL_EVALUATION.md) | Critical assertions on the release candidate, not only narrow fixtures. |

The twelve mandatory RAG subtask rows are reviewed separately:

| Subtask | Review | Evidence examined | Missing for completion |
| --- | --- | --- | --- |
| 45.1 | P | [Snapshot handling](CONTROLLED_SOURCE_SNAPSHOTS.md) | Approved-source retrieval across intended source set. |
| 45.2 | P | [PDF ingestion](PDF_SOURCE_INGESTION.md), [HTML extraction](../backend/app/knowledge/html_extraction.py) | Structure fixtures for all intended formats. |
| 45.3 | P | [Knowledge passages](../backend/app/knowledge/model.py) | Exact offset/hash provenance across every import path. |
| 45.4 | P | [Embedding index](APPROVED_EMBEDDING_INDEXING.md) | Versioned reindex and live extension checks. |
| 45.5 | P | [Search migration](../backend/migrations/versions/20261105_0006_approved_fts.py), [vector migration](../backend/migrations/versions/20261105_0007_passage_vectors.py) | Clean index build and query plan for current scale. |
| 45.6 | P | [Snapshot service](../backend/app/knowledge/snapshots.py), [review workflow](KNOWLEDGE_REVIEW_WORKFLOW.md) | Changed-source sync and approval re-review on current deployment. |
| 50.1 | P | [RAG service](../backend/app/knowledge/rag_service.py) | Context extraction and ambiguity fixtures across pilot queries. |
| 50.2 | P | [Approved search](APPROVED_PASSAGE_SEARCH.md) | Every jurisdiction/approval/version exclusion on current candidate. |
| 50.3 | P | [Vector search](../backend/app/knowledge/vector_search.py) | Representative semantic recall and extension availability. |
| 50.4 | P | [Lexical search](../backend/app/knowledge/search.py) | Representative Italian/English lexical recall. |
| 50.5 | B | [Retrieval evaluation](RETRIEVAL_EVALUATION.md) | Fusion result set and optional reranking benchmark. |
| 50.6 | P | [Quote verification](../backend/app/knowledge/quote_verification.py) | Complete citation-resolution gate across current release fixtures. |

## 8. AI agent development

| Task | Review | Evidence examined | Missing for completion |
| --- | --- | --- | --- |
| 52 | P | [Provider tests](../backend/tests/test_openrouter_provider.py), [agent guidance](CASE_AWARE_AI_GUIDANCE.md) | Current provider contract, privacy and failure evaluation. |
| 53 | P | [Preparation agent](../backend/app/preparation/agent.py) | Simulated graph path across representative procedures. |
| 54 | P | [Agent tests](../backend/tests/test_agent_e2e_mvp.py) | Explicit bilingual intent fixture and threshold evidence. |
| 55 | P | [Intake](../backend/app/preparation/intake.py), [tests](../backend/tests/test_preparation_intake.py) | Redundant-question and missing-fact matrix. |
| 56 | P | [Preparation tools](../backend/app/preparation/agent.py), [API tests](../backend/tests/test_preparation_api.py) | Tool permission and misuse checks across all enabled actions. |
| 57 | P | [Case-aware guidance](CASE_AWARE_AI_GUIDANCE.md) | Versioned plans update correctly after case/source changes. |
| 58 | P | [Milan evaluation](MILAN_MVP_ACCEPTANCE_2026_11_15.md) | Release-scale unsupported-claim and uncertainty evaluation. |
| 59 | P | [Conversation service](../backend/app/preparation/conversation.py), [tests](../backend/tests/test_preparation_conversation.py) | Resume/retry and idempotency acceptance across failures. |
| 60 | B | [Milan evaluation](MILAN_MVP_ACCEPTANCE_2026_11_15.md) | Defined agent gate on representative pilot data and provider behavior. |

## 9. Document intelligence

| Task | Review | Evidence examined | Missing for completion |
| --- | --- | --- | --- |
| 61 | B | [Vault release checklist](PRIVATE_DOCUMENT_VAULT_RELEASE.md), [security tests](../backend/tests/test_private_documents.py) | Hosted scanner, rejection and isolation gates. |
| 62 | P | [OCR tests](../backend/tests/test_private_document_intelligence.py), [staging observation](ACCEPTANCE_TESTING.md) | Text-extraction fixtures across intended formats/runtime. |
| 63 | B | [Document intelligence](PRIVATE_DOCUMENT_INTELLIGENCE.md) | Measured classification criteria and result set. |
| 64 | P | [Extraction tests](../backend/tests/test_private_document_intelligence.py) | Golden fields across pilot document types. |
| 65 | P | [Review flow](../backend/app/private_documents/intelligence.py) | End-to-end proof uncertain fields cannot silently confirm. |
| 66 | B | [Document intelligence](PRIVATE_DOCUMENT_INTELLIGENCE.md) | Cross-document mismatch and false-positive matrix. |
| 67 | P | [PDF package](../backend/app/cases/package_service.py), [tests](../backend/tests/test_case_package.py) | Prepared output matches all reviewed case data and current form. |
| 68 | B | [Vault release checklist](PRIVATE_DOCUMENT_VAULT_RELEASE.md) | Document quality gates in intended hosted environment. |

## 10. Frontend and complete workflows

| Task | Review | Evidence examined | Missing for completion |
| --- | --- | --- | --- |
| 69 | P | [App shell](../frontend/src/app/layout.tsx), [frontend CI](../.github/workflows/frontend-ci.yml) | Current responsive and accessibility baseline. |
| 70 | P | [Saved cases](../frontend/src/components/SavedCasesView.tsx), [workflow tests](../frontend/tests/case-workflow.test.mjs) | UI/API state parity under all case transitions. |
| 71 | P | [Start case](../frontend/src/components/StartCaseView.tsx), [scope tests](../frontend/tests/case-scope.test.mjs) | Supported and unsupported onboarding on current deployed revision. |
| 72 | P | [Assistant UI](../frontend/src/components/AssistantPreview.tsx), [browser acceptance](../frontend/tests/acceptance/run.mjs) | Chat E2E across intended live provider and recovery paths. |
| 73 | B | [Private workspace](../frontend/src/components/PrivateDocumentsWorkspace.tsx), [vault checklist](PRIVATE_DOCUMENT_VAULT_RELEASE.md) | Hosted document review E2E with required scanner and accounts. |
| 74 | P | [Checklist UI](../frontend/src/components/CaseJourneyPanel.tsx), [tests](../frontend/tests/case-checklist.test.mjs) | Current backend parity across corrections and rules versions. |
| 75 | P | [PDF review](../frontend/src/components/PdfReviewPanel.tsx), [case package tests](../frontend/tests/case-package.test.mjs) | Review/approval gate for every required check and correction. |
| 76 | B | [Handoff semantics](UNIFIED_CASE_WORKFLOW.md), [PDF acceptance](ACCEPTANCE_TESTING.md) | Complete reviewed journey and specific human approval for handoff. |

## 11. Testing, security and reliability

| Task | Review | Evidence examined | Missing for completion |
| --- | --- | --- | --- |
| 77 | B | [Acceptance record](ACCEPTANCE_TESTING.md) | Every release-blocking functional scenario on a release candidate. |
| 78 | B | [Retrieval evaluation](RETRIEVAL_EVALUATION.md) | Agreed agent/retrieval thresholds on representative live behavior. |
| 79 | B | [Vault checklist](PRIVATE_DOCUMENT_VAULT_RELEASE.md) | Critical document failures resolved in hosted processing. |
| 80 | P | [Milan evaluation](MILAN_MVP_ACCEPTANCE_2026_11_15.md) | Release fixture coverage and no unsupported critical claims. |
| 81 | P | [Adversarial tests](../backend/tests/test_adversarial_api_campaign.py) | Critical attack fixtures on current production-like configuration. |
| 82 | B | [Independent audit](audits/INDEPENDENT_SYSTEM_AUDIT_2026_11_06.md) | No unresolved release-blocking security/privacy finding. |
| 83 | B | [Pilot guide](MILAN_PILOT.md) | Agreed UX/accessibility gates and participant results. |
| 84 | B | [Specification §22](../PracticaMIA_Complete_Project_Specification.md#22-non-functional-requirements) | Documented load profile and budget measurements. |
| 85 | B | [CI workflows](../.github/workflows) | Representative seeded defects proven to fail CI. |
| 86 | B | [Progress gates](PROGRESS.md#outstanding-mvp-and-release-gates) | Approved release-readiness report. |

## 12. Deployment, beta and launch

| Task | Review | Evidence examined | Missing for completion |
| --- | --- | --- | --- |
| 87 | P | [Staging runbook](VERCEL_NEON_DEPLOYMENT.md), [dated checks](PROGRESS.md) | Current staging health/smoke and human approval. |
| 88 | B | [Deployment controls](VERCEL_NEON_DEPLOYMENT.md), [vault checklist](PRIVATE_DOCUMENT_VAULT_RELEASE.md) | Production security checklist and human approval. |
| 89 | P | [Dump/restore record](PROGRESS.md#november-16-follow-up) | Recovery exercise for intended data and owner approval. |
| 90 | B | [Progress gates](PROGRESS.md#outstanding-mvp-and-release-gates) | Simulated failures shown to trigger intended alerts. |
| 91 | B | [Acceptance record](ACCEPTANCE_TESTING.md) | Full staging acceptance and human approval. |
| 92 | B | [Pilot guide](MILAN_PILOT.md) | Consented real beta sessions and documented findings. |
| 93 | B | [Pilot guide](MILAN_PILOT.md) | Beta findings first, then closure of critical blockers. |
| 94 | B | [Specification §26](../PracticaMIA_Complete_Project_Specification.md#26-mvp-acceptance-criteria-and-release-gates) | Explicit owner go/no-go, live release smoke and monitoring. |

## Result and next gates

This review accounts for all 94 parent completion criteria. It records partial evidence and outstanding gaps; it certifies **zero** task completions, source approvals, human reviews, deployments or release gates. The top-level reconciliation hold may be cleared once this record and the task-level review marks are validated together. That permits selecting the earliest task whose dependencies and human gates are actually satisfied; it does not permit jumping to a later canonical task, enabling private-document production paths or declaring Phase 3's design contracts implemented. The PracticaMIA 2.0 Phase 3 catalogue also needs actual models, import batches, reviewed aliases and case-safe identity mapping before its matching behavior can serve users.
