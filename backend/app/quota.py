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