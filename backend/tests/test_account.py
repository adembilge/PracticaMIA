from uuid import uuid4
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from app.main import http_exception_handler


def test_delete_account_removes_rows_then_user(monkeypatch):
    user_id = uuid4()
    calls = []

    class FakeAdmin:
        def delete_user(self, value):
            calls.append(("user", value))

    class FakeAuth:
        admin = FakeAdmin()

    class FakeClient:
        auth = FakeAuth()
        def table(self, name):
            calls.append(("table", name))
            return self
        def delete(self):
            return self
        def eq(self, column, value):
            calls.append((column, str(value)))
            return self
        def execute(self):
            return None

    async def fake_user():
        return user_id

    monkeypatch.setattr("app.api.account.get_supabase", lambda: FakeClient())
    monkeypatch.setattr("app.api.account.current_user_id", fake_user)

    from app.auth import current_user_id as auth_current_user_id
    from app.api.account import router
    application = FastAPI()
    application.add_exception_handler(HTTPException, http_exception_handler)
    application.dependency_overrides[auth_current_user_id] = fake_user
    application.include_router(router)
    response = TestClient(application).delete("/api/account")
    assert response.status_code == 204
    assert ("table", "conversations") in calls
    assert ("table", "usage_daily") in calls
    assert ("user", str(user_id)) in calls
    assert calls.index(("table", "conversations")) < calls.index(("user", str(user_id)))


def test_delete_account_upstream_failure(monkeypatch):
    user_id = uuid4()
    calls = []

    class FakeAdmin:
        def delete_user(self, value):
            calls.append(("user", value))
            raise RuntimeError("supabase admin unavailable")

    class FakeAuth:
        admin = FakeAdmin()

    class FakeClient:
        auth = FakeAuth()
        def table(self, name):
            calls.append(("table", name))
            return self
        def delete(self):
            return self
        def eq(self, column, value):
            calls.append((column, str(value)))
            return self
        def execute(self):
            return None

    async def fake_user():
        return user_id

    monkeypatch.setattr("app.api.account.get_supabase", lambda: FakeClient())
    monkeypatch.setattr("app.api.account.current_user_id", fake_user)

    from app.auth import current_user_id as auth_current_user_id
    from app.api.account import router
    application = FastAPI()
    application.add_exception_handler(HTTPException, http_exception_handler)
    application.dependency_overrides[auth_current_user_id] = fake_user
    application.include_router(router)
    response = TestClient(application).delete("/api/account")
    assert response.status_code == 502
    assert response.json() == {
        "code": "upstream",
        "message": "The account could not be deleted.",
    }
    assert ("table", "conversations") in calls
    assert ("user", str(user_id)) in calls
    assert calls.index(("table", "conversations")) < calls.index(("user", str(user_id)))