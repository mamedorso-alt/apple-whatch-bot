from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import ReelsAgentDailyLog, User
from app.services import reels_schedule as reels_schedule_mod


def _session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)()


def test_scheduled_reels_dedup_same_day(monkeypatch):
    db = _session()
    uid = uuid4()
    db.add(
        User(
            id=uid,
            created_at=datetime.now(timezone.utc),
            timezone="UTC",
            language="ru",
            telegram_user_id=999,
            is_linked=True,
            api_token_hash="x" * 64,
        )
    )
    db.commit()

    monkeypatch.setattr(reels_schedule_mod, "_is_within_window", lambda *_a, **_kw: True)
    monkeypatch.setattr(reels_schedule_mod.settings, "reels_agent_enabled", True)
    monkeypatch.setattr(reels_schedule_mod.settings, "reels_agent_telegram_user_ids", "999")
    monkeypatch.setattr(reels_schedule_mod.settings, "scheduler_interval_min", 30)
    monkeypatch.setattr(reels_schedule_mod.settings, "default_timezone", "UTC")

    async def fake_compose(_db, _tid):
        return "SCRIPT_BODY"

    sent: list[tuple[int, str]] = []

    async def fake_chunked(chat_id: int, text: str, reply_markup: dict | None = None) -> None:
        sent.append((chat_id, text))

    monkeypatch.setattr(reels_schedule_mod, "compose_reels_script_for_telegram_user", fake_compose)
    monkeypatch.setattr(reels_schedule_mod, "send_telegram_messages_chunked", fake_chunked)

    first = asyncio.run(reels_schedule_mod.run_reels_agent_scheduled(db))
    assert first["sent"] == 1
    assert first["skipped"] == 0
    assert len(sent) == 1
    assert db.query(ReelsAgentDailyLog).count() == 1

    second = asyncio.run(reels_schedule_mod.run_reels_agent_scheduled(db))
    assert second["sent"] == 0
    assert second["skipped"] == 1
    assert len(sent) == 1


def test_scheduled_reels_off_returns_zeros(monkeypatch):
    db = _session()
    monkeypatch.setattr(reels_schedule_mod.settings, "reels_agent_enabled", False)
    out = asyncio.run(reels_schedule_mod.run_reels_agent_scheduled(db))
    assert out == {"sent": 0, "skipped": 0}
