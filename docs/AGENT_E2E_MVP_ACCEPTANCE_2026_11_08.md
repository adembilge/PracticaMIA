# PracticaMIA synthetic agent end-to-end acceptance test

**Scope:** One deliberately narrow Milan residence-change *simulation*, never a
municipal eligibility certification or real government submission.

## Automated acceptance path

`backend/tests/test_agent_e2e_mvp.py` exercises the same authenticated case
API used by the Preview UI, rather than only testing LangGraph nodes in
isolation.

| Phase | Offline acceptance assertion |
| --- | --- |
| Create and load case | Owner has access; another user receives 404 |
| First agent question | One deterministic next intake question, no inferred eligibility |
| Save intake | User explicitly confirms all five scope answers and synthetic facts |
| Determine next action | Existing rules engine requests missing fictional agreement |
| Retrieve source | Approved synthetic source produces a citation-bound exact quote |
| Upload and extract | Synthetic acknowledgement is required; extraction is not confirmation |
| Confirm and review | User explicitly confirms extracted field and document |
| Prepare package | Reviewed deterministic package has a stable digest; no submission |
| Handoff | Requires matching user review digest and still reports not submitted |
| Resume | Encrypted history can be read after the service instance is recreated |
| Revise facts | Previously approved package is invalidated; handoff is rejected |
| Delete case | Conversation and preparation metadata are removed |
| Unsupported scope | Guest or move outside Milan is not falsely called legally ineligible |

The in-memory source is **synthetic**, and a temporary SQLite fixture exercises
review approval solely inside the test process. The test model is a
deterministic `RunnableLambda` and **never calls an external provider**.

Run locally from the repository root:

```bash
cd backend
python -m pip install -e ".[dev]"
python -m pytest -q tests/test_agent_e2e_mvp.py \
  tests/test_preparation_rag.py \
  tests/test_preparation_conversation.py \
  tests/test_preparation_agent.py
```

GitHub Backend CI also runs the full backend pytest suite and disposable
PostgreSQL migrations. Frontend CI tests types, build, and localhost smoke.

## Not yet demonstrated

- Live model selection quality across Italian and English phrasing
- Actual model latency, token cost, and availability
- Auth0 login in a live Preview browser
- A live Preview API on migrated isolated PostgreSQL schema `0012`
- Legal applicability beyond source quotations and the reviewed narrow scope
- Real document handling, municipal submissions, or government status

Use synthetic-only fixtures, test credentials, and explicit Preview safeguards.
Do not treat passing this test as authorization to activate production or
as evidence of real Italian administrative eligibility.

**Next release validation:** run an authenticated, synthetic-only browser case
through the isolated Preview deployment after the Vercel quota is available,
and separately evaluate a real configured model on the approved source corpus.
