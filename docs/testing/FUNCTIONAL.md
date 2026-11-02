# Functional coverage

The suite runs on `paperpilot_functional` and drops that database. It does not migrate `paperpilot`.

- Authentication: backend/test_auth.py
- Case, intake, checklist, review: backend/test_case.py, backend/test_onboard.py, backend/test_list.py, backend/test_case_review.py, backend/test_backend.py
- Sources and retrieval: backend/test_source.py, backend/test_ingest.py, backend/test_retrieval.py, evaluation/test_retrieval.py
- Rules: backend/test_rules.py, backend/test_procedure.py, backend/test_checklist.py, backend/test_prepare.py
- Agent state: backend/test_session.py, backend/test_graph.py, backend/test_plan.py, backend/test_chat.py, evaluation/test_agent.py
- Documents: backend/test_upload.py, backend/test_papers.py, evaluation/test_documents.py
- Frontend loaders: frontend/test

pytest: 188 passed in 4.72s
node: tests 34, pass 34, fail 0
