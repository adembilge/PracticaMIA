"""Independent stress-style test of the per-user quota's race boundary.

Runs only on disposable CI PostgreSQL. Twelve workers use independent
connections; no real Auth0 subjects, model calls, or Neon branches are used.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from hashlib import sha256
import hmac
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.knowledge.usage_limit import reserve_daily_model_call

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_SMOKE") != "1",
    reason="requires disposable PostgreSQL and pooled concurrent sessions",
)


def test_parallel_attempts_cannot_exceed_approved_daily_budget():
    engine = create_engine(
        os.environ["DATABASE_URL"], pool_size=12, max_overflow=0,
        pool_timeout=15,
    )
    subject = "synthetic-stress-" + str(uuid4())
    key = "ci-only-independent-concurrent-usage-key-long-enough"
    digest = hmac.new(key.encode(), subject.encode(), "sha256").hexdigest()
    attempts = 12
    limit = 4

    def reserve(_index):
        with Session(engine) as db:
            return reserve_daily_model_call(
                db, subject=subject, hash_key=key,
                daily_limit=limit, today=date(2026, 11, 6),
            )

    try:
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(reserve, range(attempts)))
        assert sum(results) == limit
        assert len(results) == attempts
        with engine.connect() as conn:
            count = conn.execute(text("""
                SELECT request_count FROM assistant_daily_usage
                 WHERE subject_digest = :digest AND usage_day = '2026-11-06'
            """), {"digest": digest}).scalar_one()
            assert count == limit
    finally:
        # Test DB only: delete the synthetic per-test row, never any live data.
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM assistant_daily_usage WHERE subject_digest = :digest"),
                {"digest": digest},
            )
        engine.dispose()
