"""Isolated SQLite file per test, exercising the SQLAlchemy persistence layer."""
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.database import Base
from app.main import create_app
from app.cases import model  # noqa: F401


@pytest.fixture
def client(tmp_path):
    db_url = f"sqlite+pysqlite:///{tmp_path / 'cases.sqlite3'}"
    api = create_app(Settings(database_url=db_url, enable_demo_case_api=True))
    Base.metadata.create_all(api.state.engine)
    with TestClient(api) as http:
        yield http
    api.state.engine.dispose()
