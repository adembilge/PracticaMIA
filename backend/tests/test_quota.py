from datetime import date, datetime, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.quota import check_quota, increment_quota, rome_today


class FakeQuota:
    def __init__(self, user: int = 0, global_: int = 0) -> None:
        self.user = user
        self.global_ = global_

    def get_user_count(self, user_id, day: date) -> int:
        return self.user

    def get_global_count(self, day: date) -> int:
        return self.global_

    def bump(self, user_id, day: date) -> None:
        self.user += 1
        self.global_ += 1


def test_rome_rolls_to_next_local_day():
    moment = datetime(2026, 1, 15, 23, 30, tzinfo=timezone.utc)
    assert rome_today(moment) == datetime(2026, 1, 16, tzinfo=ZoneInfo("Europe/Rome")).date()


def test_user_cap():
    decision = check_quota(uuid4(), date(2026, 1, 16), FakeQuota(user=15, global_=0))
    assert decision == {"allowed": False, "reason": "user_daily"}


def test_global_cap():
    decision = check_quota(uuid4(), date(2026, 1, 16), FakeQuota(user=0, global_=40))
    assert decision == {"allowed": False, "reason": "global_daily"}


def test_increment_when_allowed():
    store = FakeQuota(user=14, global_=39)
    user_id = uuid4()
    assert check_quota(user_id, date(2026, 1, 16), store)["allowed"] is True
    increment_quota(user_id, date(2026, 1, 16), store)
    assert store.user == 15
    assert store.global_ == 40