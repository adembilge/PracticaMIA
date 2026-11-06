> Canonical roadmap excerpt from `PracticaMIA_Complete_Project_Specification.md`, §25. Do not renumber tasks. Edits to the roadmap must reconcile the canonical source and `docs/TASKS.yaml`.

# 25. Complete 12-stage, 94-task master roadmap

**Execution model:** Each numbered item is sequential by default and may have explicit dependencies on earlier tasks. Codex implements, verifies, records evidence, and moves forward only after completion requirements are satisfied. Human research, official rule approval, beta feedback, and release approval are external gates and cannot be fabricated by an agent.

## Stage 1 — Product Discovery and Definition (Tasks 1–6)

| Task | What Codex does | Completion evidence |
|---|---|---|
| **1. Define product vision** | Document intended audience, user value, strategic principles, and non-goals | Reviewed product vision; user approval |
| **2. Research user problems** | Review available evidence and prepare interview research; keep assumptions explicit | Sourced research and unresolved hypotheses |
| **3. Analyze existing solutions** | Compare official portals, services, and AI alternatives | Grounded competitor matrix and differentiation |
| **4. Define MVP boundaries** | Whitelist Milan residence-change scenarios; exclude unsupported cases | Approved in-scope/out-of-scope matrix |
| **5. Define user scenarios** | Create synthetic happy, adverse, missing-data, and out-of-scope journeys | Reference case collection with expected outcomes |
| **6. Write product specification** | Consolidate requirements and stable requirement IDs | Approved PRODUCT.md |

## Stage 2 — Government Procedure Research (Tasks 7–14)

| Task | What Codex does | Completion evidence |
|---|---|---|
| **7. Discover and classify official sources** | Identify relevant national/municipal pages and forms; record authority and RAG metadata | Auditable official source inventory |
| **8. Map the administrative procedure** | Document supported process steps, dependencies, decision branches and handoff | Reviewed workflow map |
| **9. Identify eligibility scenarios** | Enumerate supported conditions and exceptional routes | Versioned eligibility decision table |
| **10. Extract document requirements** | Record mandatory/conditional documents and evidence for each | Source-linked document catalog |
| **11. Identify deadlines and obligations** | Document applicable conditions, triggers, exceptions and dates | Reviewed deadline/obligation registry |
| **12. Research submission channels** | Identify official routes, auth prerequisites and user-only actions | Verified handoff specification |
| **13. Identify related procedures** | Separate relevant follow-ups, such as TARI, from core MVP | Classified dependency map |
| **14. Validate research and RAG sources** | Audit conflicts, freshness, approvals, and gaps; seek independent review | Approved evidence dossier or explicit blocker |

## Stage 3 — UX and Product Design (Tasks 15–20)

| Task | What Codex does | Completion evidence |
|---|---|---|
| **15. Design user journeys** | Map account creation through case preparation, handoff and resumption | Journey diagrams covering supported branches |
| **16. Design information collection** | Specify typed questions, field validators, dependencies and minimization | Reviewed intake schema |
| **17. Design conversational behavior** | Specify bilingual prompts, clarifications, unsupported replies and user review | Conversation patterns and negative examples |
| **18. Design application navigation** | Produce sitemap and mobile/desktop wireframes | Reviewed key screens and routes |
| **19. Design error and interruption states** | Specify upload errors, tool failures, blocked cases, retries and resumption | Recovery flows for major failure modes |
| **20. Prepare UI design system** | Specify components, tokens, accessibility and responsive behavior | Approved design system |

## Stage 4 — System Architecture (Tasks 21–27)

| Task | What Codex does | Completion evidence |
|---|---|---|
| **21. Define components and RAG architecture** | Map frontend, API, LangGraph, offline ingest, runtime retrieval, rules and storage | Architecture and trust boundary diagrams |
| **22. Design database and vector storage** | Model case/private data plus source versions, chunks, embeddings and full-text search | Reviewed schema and indexing plan |
| **23. Design case and agent states** | Define transitions, checkpoints, retry rules and completion semantics | Testable state machines |
| **24. Design requirements and evidence engine** | Model tri-state conditions, rule versions, source links and approval workflow | Rules schema representing all approved fixtures |
| **25. Design document processing** | Define secure ingest, extraction, review, validation and form mapping | Document pipeline design |
| **26. Design security and privacy controls** | Model threats, authorization, provider exposure, retention and approval boundaries | Reviewed security/privacy design |
| **27. Define API and retrieval contracts** | Specify typed service contracts for tools, RAG, rules and user-facing routes | Approved interface specifications |

## Stage 5 — Codex and Development Environment (Tasks 28–35)

| Task | What Codex does | Completion evidence |
|---|---|---|
| **28. Create Codex instructions** | Establish AGENTS.md, coding policy, no invented government rules, mandatory tests | Reviewed persistent agent instructions |
| **29. Build execution backlog** | Translate approved roadmap into structured task records and dependencies | Exactly 94 validated task IDs |
| **30. Implement progress tracking** | Track current status, evidence, approvals, decisions and blockers | Fresh session reconstructs state |
| **31. Initialize application structure** | Create monorepo, package boundaries and developer documentation | Repository integrity checks pass |
| **32. Configure RAG and application dependencies** | Pin Python/JS dependencies, pgvector and embedding adapters | Reproducible installs and DB extension |
| **33. Configure local infrastructure** | Set up Docker Compose, database, private volumes, environment template | Clean checkout boots services |
| **34. Establish automated and RAG verification** | Configure lint, typing, CI, pytest, retrieval fixtures and Playwright baseline | Mandatory checks run and report failures |
| **35. Verify autonomous development workflow** | Exercise worktree, one-task execution, tests, status updates and approval stop | Reproducible sample iteration |

## Stage 6 — Backend Foundation (Tasks 36–43)

| Task | What Codex does | Completion evidence |
|---|---|---|
| **36. Initialize FastAPI** | Create configuration, routers, errors, health endpoints and API docs | API smoke/unit tests pass |
| **37. Implement database models and migrations** | Create scoped schema, constraints, indexes and Alembic migrations | Fresh migration and integrity checks pass |
| **38. Implement authentication** | Add vetted session/account auth and safe login/logout | Positive/negative auth tests pass |
| **39. Implement authorization** | Enforce case/document ownership and privileged source review | Cross-user reads and writes denied |
| **40. Implement user profiles** | Store minimum necessary personal fields with correction controls | CRUD and validation tests pass |
| **41. Implement case management** | Create stateful case APIs and audit events | Lifecycle and invalid-transition tests pass |
| **42. Implement secure document storage** | Add private uploads, metadata, file validation, retrieval and deletion | Unsafe upload and cross-account tests pass |
| **43. Complete backend integration tests** | Exercise DB, auth, errors, cases, files with isolated fixtures | Backend integration suite passes |

## Stage 7 — Government Knowledge Engine (Tasks 44–51)

| Task | What Codex does | Completion evidence |
|---|---|---|
| **44. Implement official source registry** | Store jurisdiction, authority, reviewed version, status and approval | Versioned registry works with permissions |
| **45. Implement RAG ingestion and indexing** | Build collection, extraction, chunking, embeddings, pgvector/text indexes, and source syncing (45.1–45.6) | Indexed approved passages trace to exact versions |
| **46. Implement structured requirements with evidence links** | Encode approved rules and exact passage references | No unreviewed rule activated |
| **47. Build deterministic rules evaluator** | Evaluate condition trees with TRUE/FALSE/UNKNOWN | Golden rule cases pass |
| **48. Build procedure selection** | Identify supported, unknown and unsupported routes from confirmed facts | Routing fixtures pass |
| **49. Build checklist generator** | Turn applicable rules into dependent actions and required documents | Checklist golden cases pass |
| **50. Implement hybrid retrieval and citation resolution** | Build query processing, filters, vector/keyword search, fusion, optional reranking, citations (50.1–50.6) | Retrieval respects jurisdiction/approval/version and cites evidence |
| **51. Validate knowledge engine and RAG** | Test Recall@K, MRR, citation accuracy, conflicts, stale sources and rule logic | Critical retrieval/rule assertions pass |

**Task 45 mandatory subtasks:** 45.1 retrieve approved source snapshots; 45.2 parse HTML/PDF structure; 45.3 create provenance-preserving chunks; 45.4 generate versioned embeddings; 45.5 build pgvector and lexical indexes; 45.6 detect changes and synchronize only with appropriate review.

**Task 50 mandatory subtasks:** 50.1 understand query context; 50.2 enforce metadata filters; 50.3 semantic retrieval; 50.4 full-text retrieval; 50.5 fusion and optional benchmarked reranking; 50.6 evidence and citation assembly.

## Stage 8 — AI Agent Development (Tasks 52–60)

| Task | What Codex does | Completion evidence |
|---|---|---|
| **52. Implement LLM integration** | Create model adapter, structured generation, limits, retries and provider mocks | Contract and provider failure tests pass |
| **53. Build LangGraph and RAG-aware workflow** | Create graph with explicit tool/retrieval/rules steps and interrupts | Simulated graph path executes correctly |
| **54. Implement intent understanding** | Route user requests to supported procedure and task types | Bilingual intent fixtures pass |
| **55. Implement intelligent intake** | Ask needed questions from typed schemas; preserve confirmed context | No redundant questions; missing facts handled |
| **56. Implement RAG and administrative agent tools** | Expose 14 narrowly scoped tools with typed contracts and authorization | Tool and permissions tests pass |
| **57. Implement evidence-grounded case planning** | Plan actions from verified rules plus retrieved explanation | Plans cite valid rules/evidence and update |
| **58. Implement grounding and uncertainty handling** | Handle stale/missing sources, contradictory facts, injection and insufficient evidence | No fabricated critical claims in test set |
| **59. Implement persistence and recovery** | Persist graph checkpoints, idempotency and interrupted runs | Resume and retry tests pass |
| **60. Evaluate RAG-enhanced initial agent** | Benchmark groundedness, choices, routing, planning, cost and recovery | Agent evaluation gate passes |

## Stage 9 — Document Intelligence (Tasks 61–68)

| Task | What Codex does | Completion evidence |
|---|---|---|
| **61. Implement document ingestion safeguards** | Validate bytes/MIME, limits and hostile file handling | Unsafe and malformed file tests pass |
| **62. Implement PDF and image extraction** | Combine PyMuPDF with OCR and preserve source spans | Text extraction fixtures pass |
| **63. Implement document classification** | Classify supported, unknown and ambiguous types | Classification criteria met |
| **64. Implement structured field extraction** | Extract case-relevant fields and preserve provenance | Golden field extraction cases pass |
| **65. Implement extraction confidence handling** | Require review for uncertain or critical values | No silent confirmation of uncertain data |
| **66. Implement cross-document validation** | Compare document values, user input and confirmed facts | Mismatch and false-positive tests pass |
| **67. Implement application preparation** | Map confirmed values to reviewed template/summary and check blockers | Output matches reviewed case data |
| **68. Evaluate document intelligence** | Benchmark OCR, field accuracy, conflicts, package generation and privacy | Document quality gates pass |

## Stage 10 — Frontend and Complete Workflows (Tasks 69–76)

| Task | What Codex does | Completion evidence |
|---|---|---|
| **69. Implement application shell** | Build Next.js routes, authentication UI, i18n and design system | Responsive/accessibility baseline passes |
| **70. Implement case dashboard** | Show owner-scoped cases, statuses and outstanding actions | UI and API state consistent |
| **71. Implement case onboarding** | Capture goal, route/unsupported flags, create saved case | Supported and unsupported onboarding tested |
| **72. Implement agent conversation interface** | Render structured prompts, messages, activities and resumption | Chat E2E tests pass |
| **73. Implement document workspace** | Upload, preview, inspect and correct extracted fields | Document review E2E passes |
| **74. Implement interactive checklists** | Render source-linked requirements, dependencies and live progress | Checklist remains consistent with backend |
| **75. Implement evidence and application review** | Show citations, verified fields, blockers and approval step | Approval blocked until checks pass |
| **76. Implement official submission handoff** | Display verified portal guidance and correctly record user-reported state | Complete journey reaches submission-ready, not falsely submitted |

## Stage 11 — Testing, Security and Reliability (Tasks 77–86)

| Task | What Codex does | Completion evidence |
|---|---|---|
| **77. Run comprehensive functional tests** | Close unit/API/integration coverage gaps across services | All release-blocking functional tests pass |
| **78. Evaluate agent and RAG correctness** | Run reviewed multi-turn cases with versioned expected outcomes | Targeted agent/retrieval thresholds pass |
| **79. Evaluate document-processing accuracy** | Measure field classification, extraction and package errors | Critical document failures resolved |
| **80. Test grounding and citation accuracy** | Challenge stale, missing, conflicting or incorrectly cited evidence | No critical unsupported claims in release fixtures |
| **81. Test adversarial inputs** | Exercise prompt injection, tool misuse and malformed content | Critical attack fixtures blocked |
| **82. Perform privacy and security verification** | Inspect access controls, PII handling, retention and deletion | No unresolved release-blocking finding |
| **83. Test usability and accessibility** | Run Playwright, language, keyboard, mobile and user-journey tests | Agreed UX/accessibility gates met |
| **84. Evaluate performance and costs** | Benchmark latency, throughput, model tokens and per-case cost | Budgets met with documented load |
| **85. Verify RAG and agent regression protection** | Ensure CI checks citation, rules, retrieval and agent behavior on changes | Representative seeded defects cause CI failure |
| **86. Conduct final release acceptance** | Compile complete evidence and obtain go/no-go human decision | Approved release-readiness report |

## Stage 12 — Deployment, Beta and Launch (Tasks 87–94)

| Task | What Codex does | Completion evidence |
|---|---|---|
| **87. Prepare staging infrastructure** | Deploy isolated Docker/VPS staging services | Staging health and smoke tests pass |
| **88. Configure production security** | Prepare TLS, firewall, secret storage, restricted access | Deployment security checklist passes |
| **89. Implement backup and recovery** | Configure encrypted backups and test restoration | Restored data integrity verified |
| **90. Implement operational and RAG monitoring** | Alert on errors, cost anomalies, source/index failures and tool failures | Simulated failures trigger alerts |
| **91. Verify deployment behavior** | Test migrations, rollback, full case flow and health in staging | Staging acceptance passes |
| **92. Conduct private beta** | Prepare beta process; collect actual authorized participant feedback | Real beta evidence documented |
| **93. Resolve beta findings** | Fix approved prioritized issues and rerun regression tests | Critical beta blockers closed |
| **94. Prepare and execute public release** | Package production release, document limitations, deploy after approval | Owner approval, live smoke tests and monitoring verified |

## Roadmap governance

- Maintain **exactly 94 parent tasks** and retain the stable IDs. Tasks 45 and 50 have six numbered subtasks each; these do not renumber subsequent parent tasks.
- At the start of each execution, confirm dependency and approval status. A task may be `blocked` rather than completed.
- Human research/approval tasks cannot be satisfied by model-generated statements about imaginary interviews, legal review, or beta users.
- Tasks can be revisited if their source rules, dependencies, or security assumptions change.
- The next build task should be expanded into a small executable implementation specification with files, tests and acceptance checks.
