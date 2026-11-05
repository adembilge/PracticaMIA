"""Deterministic user-isolated persistent quota tests without provider calls."""
from datetime import date, timedelta
from sqlalchemy import text

from app.knowledge.usage_limit import reserve_daily_model_call

KEY = "unit-test-only-usage-secret-material-32-bytes"
DAY = date(2026, 11, 5)


def reserve(db, name, limit=2, today=DAY):
    return reserve_daily_model_call(
        db, subject=name, hash_key=KEY,
        daily_limit=limit, today=today,
    )


def test_quota_is_shared_per_subject_and_across_sessions(client):
    factory = client.app.state.session_factory
    with factory() as db:
        assert reserve(db, "alice")
    with factory() as db:
        assert reserve(db, "alice")
    with factory() as db:
        assert not reserve(db, "alice")
        assert reserve(db, "bob")
        rows = db.execute(text(
            "SELECT subject_digest, request_count FROM assistant_daily_usage"
        )).all()
        assert len(rows) == 2
        assert all(x.subject_digest != "alice" and x.subject_digest != "bob" for x in rows)
        assert sorted(x.request_count for x in rows) == [1, 2]


def test_quota_resets_on_new_utc_day_and_expires_old_rows(client):
    factory = client.app.state.session_factory
    with factory() as db:
        assert reserve(db, "alice", limit=1)
        assert not reserve(db, "alice", limit=1)
        assert reserve(db, "alice", limit=1, today=DAY + timedelta(days=1))
        # A new event purges daily rows older than 30 days.
        assert reserve(db, "bob", limit=1, today=DAY + timedelta(days=33))
        assert db.execute(text(
            "SELECT count(*) FROM assistant_daily_usage"
        )).scalar_one() == 1


def test_quota_rejects_bad_secrets_limits_and_identifiers(client):
    import pytest
    with client.app.state.session_factory() as db:
        for kwargs in [
            {"subject": "", "hash_key": KEY, "daily_limit": 5},
            {"subject": "alice", "hash_key": "too-short", "daily_limit": 5},
            {"subject": "alice", "hash_key": KEY, "daily_limit": 0},
            {"subject": "alice", "hash_key": KEY, "daily_limit": 51},
        ]:
            with pytest.raises(ValueError):
                reserve_daily_model_call(db, **kwargs)
