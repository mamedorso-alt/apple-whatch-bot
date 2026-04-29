import asyncio
from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import DailyMetric, DailyScore, MessageLog, User
from app.services import scheduler as scheduler_service
from app.services.scheduler import run_scheduled_reports


def _make_db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)()


def test_scheduler_window_logic():
    now = datetime(2026, 4, 29, 8, 35, 0, tzinfo=timezone.utc)
    scheduler_service.settings.morning_send_hour = 8
    scheduler_service.settings.morning_send_minute = 30
    scheduler_service.settings.evening_send_hour = 20
    scheduler_service.settings.evening_send_minute = 30
    scheduler_service.settings.scheduler_interval_min = 30
    assert scheduler_service._message_type_for_local_time(now) == "morning"


def test_scheduler_dedup_same_day(monkeypatch):
    db = _make_db()
    user_id = uuid4()
    user = User(
        id=user_id,
        created_at=datetime.now(timezone.utc),
        timezone="UTC",
        language="en",
        telegram_user_id=777,
        is_linked=True,
        api_token_hash="hash",
    )
    db.add(user)
    db.add(
        DailyMetric(
            user_id=user_id,
            date=date.today(),
            steps=7000,
            active_kcal=300,
            sleep_min=420,
            sleep_start=None,
            sleep_end=None,
            resting_hr=None,
            hrv_sdnn=None,
            workouts_count=1,
            updated_at=datetime.now(timezone.utc),
        )
    )
    db.add(
        DailyScore(
            user_id=user_id,
            date=date.today(),
            focus_score=72,
            mode="normal",
            reasons_json={"items": []},
        )
    )
    db.commit()

    async def fake_send_message(*_args, **_kwargs):
        return None

    monkeypatch.setattr("app.services.scheduler.send_telegram_message", fake_send_message)
    monkeypatch.setattr("app.services.scheduler._message_type_for_local_time", lambda _dt: "morning")

    asyncio.run(run_scheduled_reports(db))
    asyncio.run(run_scheduled_reports(db))

    rows = db.query(MessageLog).all()
    assert len(rows) == 1
    assert rows[0].message_type == "morning"
