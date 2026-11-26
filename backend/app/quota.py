from datetime import date, datetime
from typing import Literal, TypedDict
from uuid import UUID
from zoneinfo import ZoneInfo

from app.config import get_settings

ROME = ZoneInfo("Europe/Rome")


class QuotaDecision(TypedDict):
    allowed: bool
    reason: Literal["ok", "user_daily", "global_daily"]


def rome_today(now: datetime | None = None) -> date:
    if now is None:
        moment = datetime.now(ROME)
    else:
        moment = now.astimezone(ROME)
    return moment.date()


def check_quota(user_id: UUID, today: date, store) -> QuotaDecision:
    settings = get_settings()
    if store.get_user_count(user_id, today) >= settings.user_daily_limit:
        return {"allowed": False, "reason": "user_daily"}
    if store.get_global_count(today) >= settings.global_daily_limit:
        return {"allowed": False, "reason": "global_daily"}
    return {"allowed": True, "reason": "ok"}


def increment_quota(user_id: UUID, today: date, store) -> None:
    store.bump(user_id, today)


class SupabaseQuotaStore:
    def __init__(self, client) -> None:
        self._client = client

    def get_user_count(self, user_id: UUID, today: date) -> int:
        found = self._read(
            "usage_daily",
            {"user_id": str(user_id), "day": today.isoformat()},
        )
        return 0 if found is None else found

    def get_global_count(self, today: date) -> int:
        found = self._read("global_usage_daily", {"day": today.isoformat()})
        return 0 if found is None else found

    def bump(self, user_id: UUID, today: date) -> None:
        day = today.isoformat()
        uid = str(user_id)
        self._increment(
            "usage_daily",
            {"user_id": uid, "day": day},
            {"user_id": uid, "day": day},
        )
        self._increment(
            "global_usage_daily",
            {"day": day},
            {"day": day},
        )

    def _read(self, table: str, filters: dict) -> int | None:
        query = self._client.table(table).select("request_count")
        for column, value in filters.items():
            query = query.eq(column, value)
        resp = query.limit(1).execute()
        rows = resp.data or []
        if not rows:
            return None
        return int(rows[0]["request_count"])

    def _increment(self, table: str, filters: dict, identity: dict) -> None:
        current = self._read(table, filters)
        if current is None:
            row = dict(identity)
            row["request_count"] = 1
            self._client.table(table).insert(row).execute()
            return
        query = self._client.table(table).update({"request_count": current + 1})
        for column, value in filters.items():
            query = query.eq(column, value)
        query.execute()