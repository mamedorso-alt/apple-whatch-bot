from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.db.models import DailyMetric, DailyScore, LinkCode, MessageLog, User


class FakeQuery:
    def __init__(self, items):
        self._items = list(items)

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def first(self):
        return self._items[0] if self._items else None

    def all(self):
        return list(self._items)


class FakeSession:
    def __init__(self):
        self.users: list[User] = []
        self.link_codes: list[LinkCode] = []
        self.daily_metrics: list[DailyMetric] = []
        self.daily_scores: list[DailyScore] = []
        self.message_logs: list[MessageLog] = []

    def query(self, model):
        mapping = {
            User: self.users,
            LinkCode: self.link_codes,
            DailyMetric: self.daily_metrics,
            DailyScore: self.daily_scores,
            MessageLog: self.message_logs,
        }
        return FakeQuery(mapping.get(model, []))

    def add(self, obj):
        if isinstance(obj, User):
            self.users.append(obj)
        elif isinstance(obj, LinkCode):
            self.link_codes.append(obj)
        elif isinstance(obj, DailyMetric):
            self.daily_metrics.append(obj)
        elif isinstance(obj, DailyScore):
            self.daily_scores.append(obj)
        elif isinstance(obj, MessageLog):
            self.message_logs.append(obj)

    def commit(self):
        return None

    def refresh(self, _obj):
        return None

    def rollback(self):
        return None


def make_user(language: str = "ru", telegram_user_id: int | None = None) -> User:
    return User(
        id=uuid4(),
        created_at=datetime.now(timezone.utc),
        timezone="Asia/Baku",
        language=language,
        telegram_user_id=telegram_user_id,
        is_linked=telegram_user_id is not None,
        api_token_hash="hash",
    )


def make_link_code(user_id, code: str = "ABC123") -> LinkCode:
    return LinkCode(
        id=1,
        user_id=user_id,
        code=code,
        expires_at=datetime.now(timezone.utc).replace(year=2099),
        used_at=None,
    )


def make_metric(user_id, day, sleep_min: int = 420, steps: int = 8000, active_kcal: float = 300.0) -> DailyMetric:
    return DailyMetric(
        id=1,
        user_id=user_id,
        date=day,
        steps=steps,
        active_kcal=active_kcal,
        sleep_min=sleep_min,
        sleep_start=None,
        sleep_end=None,
        resting_hr=55,
        hrv_sdnn=40,
        workouts_count=1,
        updated_at=datetime.now(timezone.utc),
    )


def ns(**kwargs):
    return SimpleNamespace(**kwargs)
