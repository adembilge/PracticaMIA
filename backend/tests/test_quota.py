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


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, client, name: str) -> None:
        self.client = client
        self.name = name
        self.filters: list[tuple[str, object]] = []
        self.op: str | None = None
        self.payload = None

    def select(self, *_columns):
        self.op = "select"
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def limit(self, _count):
        return self

    def update(self, payload):
        self.op = "update"
        self.payload = payload
        return self

    def insert(self, payload):
        self.op = "insert"
        self.payload = payload
        return self

    def upsert(self, payload, on_conflict=None):
        self.client.upserts.append((self.name, payload, on_conflict))
        self.op = "upsert"
        self.payload = payload
        return self

    def execute(self):
        rows = self.client.rows.setdefault(self.name, [])

        def matches(row):
            return all(row.get(column) == value for column, value in self.filters)

        if self.op == "select":
            return _Result([row for row in rows if matches(row)])
        if self.op == "update":
            matched = []
            for row in rows:
                if matches(row):
                    row.update(self.payload)
                    matched.append(row)
            return _Result(matched)
        if self.op == "insert":
            rows.append(dict(self.payload))
            return _Result([self.payload])
        if self.op == "upsert":
            return _Result([self.payload])
        raise AssertionError(f"unexpected op {self.op}")


class RecordingQuotaClient:
    def __init__(self) -> None:
        self.rows: dict[str, list[dict]] = {}
        self.upserts: list = []

    def table(self, name: str):
        return _Query(self, name)


def test_supabase_quota_store_reads_then_increments():
    from app.quota import SupabaseQuotaStore

    user_id = uuid4()
    day = date(2026, 1, 16)
    client = RecordingQuotaClient()
    client.rows["usage_daily"] = [
        {"user_id": str(user_id), "day": day.isoformat(), "request_count": 4}
    ]
    client.rows["global_usage_daily"] = [
        {"day": day.isoformat(), "request_count": 9}
    ]
    store = SupabaseQuotaStore(client)
    assert store.get_user_count(user_id, day) == 4
    assert store.get_global_count(day) == 9
    store.bump(user_id, day)
    assert store.get_user_count(user_id, day) == 5
    assert store.get_global_count(day) == 10

    empty = RecordingQuotaClient()
    empty_store = SupabaseQuotaStore(empty)
    other = uuid4()
    assert empty_store.get_user_count(other, day) == 0
    assert empty_store.get_global_count(day) == 0
    empty_store.bump(other, day)
    assert empty_store.get_user_count(other, day) == 1
    assert empty_store.get_global_count(day) == 1
    assert client.upserts == []
    assert empty.upserts == []