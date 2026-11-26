from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.main import http_exception_handler


def test_list_sources_omits_content_and_selects_columns(monkeypatch):
    user_id = uuid4()
    select_args = []

    class FakeResult:
        def __init__(self, data):
            self.data = data

    class FakeQuery:
        def select(self, columns):
            select_args.append(columns)
            return self

        def execute(self):
            return FakeResult(
                [
                    {
                        "id": "src-1",
                        "name": "Example",
                        "topic": "residence",
                        "batch": "a",
                        "portal_url": "https://example.gov",
                        "last_crawled_at": "2026-01-15T10:00:00+00:00",
                        "status": "ok",
                        "content": "secret chunk text",
                    }
                ]
            )

    class FakeClient:
        def table(self, name):
            assert name == "sources"
            return FakeQuery()

    async def fake_user():
        return user_id

    monkeypatch.setattr("app.api.sources.get_supabase", lambda: FakeClient())

    from app.auth import current_user_id as auth_current_user_id
    from app.api.sources import router

    application = FastAPI()
    application.add_exception_handler(HTTPException, http_exception_handler)
    application.dependency_overrides[auth_current_user_id] = fake_user
    application.include_router(router)
    response = TestClient(application).get(
        "/api/sources",
        headers={"Authorization": "Bearer fake"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert "content" not in body[0]
    assert body[0] == {
        "id": "src-1",
        "name": "Example",
        "topic": "residence",
        "batch": "a",
        "portal_url": "https://example.gov",
        "last_crawled_at": "2026-01-15T10:00:00+00:00",
        "status": "ok",
    }
    assert select_args == ["id,name,topic,batch,portal_url,last_crawled_at,status"]


def test_list_sources_without_auth_is_401():
    from app.api.sources import router

    application = FastAPI()
    application.add_exception_handler(HTTPException, http_exception_handler)
    application.include_router(router)
    response = TestClient(application).get("/api/sources")
    assert response.status_code == 401