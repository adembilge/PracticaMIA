"""Atomic, shared per-user daily LLM limit; no raw Auth0 IDs are stored.

A keyed hash prevents trivial recovery of the subject from its digest. Calls
are reserved *before* contacting the external model. This is a cost/safety
boundary, not a general-purpose abuse-prevention WAF or IP rate limiter.
"""
from datetime import date, datetime, timedelta, timezone
import hashlib
import hmac

from sqlalchemy import text
from sqlalchemy.orm import Session


def reserve_daily_model_call(
    db: Session, *, subject: str, hash_key: str, daily_limit: int,
    today: date | None = None,
) -> bool:
    if not subject or len(hash_key) < 32 or not 1 <= daily_limit <= 50:
        raise ValueError("Assistant usage policy is invalid")
    today = today or datetime.now(timezone.utc).date()
    digest = hmac.new(
        hash_key.encode("utf-8"), subject.encode("utf-8"), hashlib.sha256,
    ).hexdigest()
    # Expired entries are purged opportunistically on subsequent requests.
    db.execute(text("""
        DELETE FROM assistant_daily_usage WHERE usage_day < :cutoff
    """), {"cutoff": (today - timedelta(days=30)).isoformat()})
    result = db.execute(text("""
        INSERT INTO assistant_daily_usage
            (subject_digest, usage_day, request_count)
        VALUES (:digest, :day, 1)
        ON CONFLICT (subject_digest, usage_day)
        DO UPDATE SET request_count = assistant_daily_usage.request_count + 1
        WHERE assistant_daily_usage.request_count < :limit
        RETURNING request_count
    """), {
        "digest": digest, "day": today.isoformat(), "limit": daily_limit,
    }).scalar_one_or_none()
    # Commit the reservation before the model call, preventing retries or
    # provider failures from bypassing a shared multi-instance quota.
    db.commit()
    return result is not None
