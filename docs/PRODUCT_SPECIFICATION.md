# PracticaMIA — product specification

## Purpose

PracticaMIA is an independent English–Italian conversational assistant for navigating Italian administrative procedures. It helps a person understand a supported procedure, identify what information is missing, review official evidence and prepare their next step.

It is not a government authority, legal representative or submission channel. It does not use SPID/CIE credentials, sign, pay or submit applications on the user's behalf.

## Initial scope

The first reviewed scope is an individual residence-change scenario in Comune di Milano. This narrow scope is not a claim that every residence, household, citizenship or housing situation is supported. When the request falls outside reviewed coverage, the assistant must say so and avoid extrapolating rules.

## Customer experience

The product has exactly one primary customer interface: a ChatGPT-style conversation at `/`.

- A user starts with free text. No task, procedure or authority needs to be selected first.
- The assistant identifies likely intent and asks only the clarification needed to distinguish supported routes.
- Answers show the applicable official evidence and make uncertainty visible.
- Confirmed facts, corrections, approvals, checklists, documents and next actions appear as inline messages or cards.
- The sidebar contains conversation history only.
- No customer-facing task selector, dashboard, document portal, form editor, source browser or synthetic demo is part of the product.

## Agent behavior

The agent is a single specialist workflow. It combines typed intent extraction, reviewed catalogue matching, approved-source retrieval, deterministic applicability checks, clarification and resumable execution.

The model may assist with language understanding, but the server owns identity, authorization, jurisdiction, source approval, rule versions, state transitions and writes. A model suggestion cannot establish authority competence or legal applicability.

## Evidence and source policy

A consequential administrative claim requires a current, approved, provenance-preserving source passage that supports that exact claim and applies to the confirmed procedure, location, date and circumstances.

If the evidence is missing, stale, contradictory or insufficient, the assistant must abstain, explain the verification gap or request human review. A general authority URL is not proof of a specific fee, deadline, requirement or eligibility condition.

## User data and approvals

User statements, document extraction and agent suggestions have distinct provenance. Extracted values are not confirmed facts. A proposed change must show its meaning and remain unapplied until explicit user approval. Stale approvals and duplicate writes must be rejected.

Internal task/workflow records preserve facts, permissions, revisions and resumption. They are private implementation state, not a customer-facing product entity. Some backend modules, routes and tables still use historical case terminology; their migration is tracked in [LEGACY_MIGRATION_PLAN.md](LEGACY_MIGRATION_PLAN.md). Existing database records must not be deleted or reassigned during UI cleanup.

## Documents and government actions

Real personal-document upload and OCR are disabled until independent privacy, malware scanning, encryption/key management, retention, backup and operational reviews pass. Any future document review must happen inline in the conversation.

The user completes required login, signing, payment and submission directly through a verified official service. PracticaMIA must never claim that a draft, checklist, PDF or user-reported action is government-confirmed.

## Architecture

- Frontend: Next.js 15, React 19 and TypeScript.
- API: Python 3.12 and FastAPI.
- Identity: Auth0 sessions and server-side access-token forwarding.
- Agent: LangGraph with typed state, resumable events and bounded tool execution.
- Knowledge: PostgreSQL full-text search and pgvector with source/passage provenance.
- Rules: deterministic Python evaluation with reviewed, versioned catalogues.
- Persistence: PostgreSQL and Alembic.
- Quality: pytest, Node tests, TypeScript, Next.js build and isolated browser/database checks.

## Release status

The single-chat shell is the root UI. The authenticated conversation transport and worker remain restricted to isolated development/Preview infrastructure and are not production-enabled. The current agent work is synthetic engineering validation, not live legal validation or production acceptance.

Phase 4 remains active. Phase 5 is paused until separately authorized.
