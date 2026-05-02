from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app


def _setup_test_db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return engine


def test_webhook_reel_runs_manual_delivery_for_allowlist(monkeypatch):
    _setup_test_db()
    monkeypatch.setenv("REELS_AGENT_ENABLED", "true")
    monkeypatch.setenv("REELS_AGENT_TELEGRAM_USER_IDS", "777")
    get_settings.cache_clear()

    calls: list[tuple[int, int]] = []

    async def fake_manual(db, telegram_user_id: int, chat_id: int) -> None:
        calls.append((telegram_user_id, chat_id))

    monkeypatch.setattr("app.api.routes.telegram.run_reels_manual_delivery", fake_manual)

    settings = get_settings()
    webhook_headers = {}
    if settings.telegram_webhook_secret:
        webhook_headers["X-Telegram-Bot-Api-Secret-Token"] = settings.telegram_webhook_secret

    client = TestClient(app)
    r = client.post(
        "/v1/telegram/webhook",
        json={"message": {"text": "/reel", "chat": {"id": 777}, "from": {"id": 777}}},
        headers=webhook_headers,
    )
    assert r.status_code == 200
    assert calls == [(777, 777)]
    get_settings.cache_clear()


def test_webhook_reel_button_text_same_as_manual(monkeypatch):
    _setup_test_db()
    monkeypatch.setenv("REELS_AGENT_ENABLED", "true")
    monkeypatch.setenv("REELS_AGENT_TELEGRAM_USER_IDS", "777")
    get_settings.cache_clear()

    calls: list[int] = []

    async def fake_manual(db, telegram_user_id: int, chat_id: int) -> None:
        calls.append(telegram_user_id)

    monkeypatch.setattr("app.api.routes.telegram.run_reels_manual_delivery", fake_manual)

    settings = get_settings()
    webhook_headers = {}
    if settings.telegram_webhook_secret:
        webhook_headers["X-Telegram-Bot-Api-Secret-Token"] = settings.telegram_webhook_secret

    client = TestClient(app)
    r = client.post(
        "/v1/telegram/webhook",
        json={
            "message": {
                "text": "🎬 Сценарий рилса",
                "chat": {"id": 777},
                "from": {"id": 777},
            }
        },
        headers=webhook_headers,
    )
    assert r.status_code == 200
    assert calls == [777]
    get_settings.cache_clear()


def test_webhook_reel_not_allowlisted_sends_message(monkeypatch):
    _setup_test_db()
    monkeypatch.setenv("REELS_AGENT_ENABLED", "true")
    monkeypatch.setenv("REELS_AGENT_TELEGRAM_USER_IDS", "777")
    get_settings.cache_clear()

    sent: list[str] = []

    async def capture_send(chat_id: int, text: str, reply_markup: dict | None = None) -> None:
        sent.append(text)

    monkeypatch.setattr("app.api.routes.telegram.send_telegram_message", capture_send)

    settings = get_settings()
    webhook_headers = {}
    if settings.telegram_webhook_secret:
        webhook_headers["X-Telegram-Bot-Api-Secret-Token"] = settings.telegram_webhook_secret

    client = TestClient(app)
    r = client.post(
        "/v1/telegram/webhook",
        json={"message": {"text": "/reel", "chat": {"id": 999}, "from": {"id": 999}}},
        headers=webhook_headers,
    )
    assert r.status_code == 200
    assert len(sent) == 1
    assert "разреш" in sent[0].lower() or "allowlist" in sent[0].lower()
    get_settings.cache_clear()


def test_webhook_start_includes_reels_keyboard_for_allowlist(monkeypatch):
    _setup_test_db()
    monkeypatch.setenv("REELS_AGENT_ENABLED", "true")
    monkeypatch.setenv("REELS_AGENT_TELEGRAM_USER_IDS", "777")
    get_settings.cache_clear()

    markups: list[dict | None] = []

    async def capture_send(chat_id: int, text: str, reply_markup: dict | None = None) -> None:
        markups.append(reply_markup)

    monkeypatch.setattr("app.api.routes.telegram.send_telegram_message", capture_send)

    settings = get_settings()
    webhook_headers = {}
    if settings.telegram_webhook_secret:
        webhook_headers["X-Telegram-Bot-Api-Secret-Token"] = settings.telegram_webhook_secret

    client = TestClient(app)
    r = client.post(
        "/v1/telegram/webhook",
        json={"message": {"text": "/start", "chat": {"id": 777}, "from": {"id": 777}}},
        headers=webhook_headers,
    )
    assert r.status_code == 200
    assert markups and markups[0] and "keyboard" in markups[0]
    assert "🎬" in markups[0]["keyboard"][0][0]["text"]
    get_settings.cache_clear()
