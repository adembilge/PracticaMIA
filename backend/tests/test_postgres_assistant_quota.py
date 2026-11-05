"""PostgreSQL integration check for the shared atomic assistant budget."""
import os
from datetime import date

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.knowledge.usage_limit import reserve_daily_model_call

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_SMOKE") != "1",
    reason="requires migrated disposable PostgreSQL",
)


def test_postgres_daily_quota_is_transactional_and_pseudonymous():
    engine = create_engine(os.environ["DATABASE_URL"])
    try:
        with engine.connect() as conn:
            transaction = conn.begin()
            try:
                assert conn.execute(text(
                    "SELECT to_regclass('public.assistant_daily_usage')"
                )).scalar() == "assistant_daily_usage"
                factory = sessionmaker(bind=conn, expire_on_commit=False)
                key = "postgres-ci-test-secret-do-not-use-in-production"
                def reserve(subject):
                    with factory() as db:
                        return reserve_daily_model_call(
                            db, subject=subject, hash_key=key,
                            daily_limit=2, today=date(2026, 11, 5),
                        )
                assert reserve("alice")
                assert reserve("alice")
                assert not reserve("alice")
                assert reserve("bob")
                rows = conn.execute(text(
                    "SELECT subject_digest, request_count FROM assistant_daily_usage"
                )).all()
                assert len(rows) == 2
                assert sorted(row.request_count for row in rows) == [1, 2]
                assert all(len(row.subject_digest) == 64 for row in rows)
            finally:
                transaction.rollback()
    finally:
        engine.dispose()
