from __future__ import annotations

from datetime import date
from decimal import Decimal

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


def test_end_to_end_api_flow(monkeypatch):
    _setup_test_db()
    settings = get_settings()

    async def fake_send_message(*_args, **_kwargs):
        return None

    monkeypatch.setattr("app.api.routes.telegram.send_telegram_message", fake_send_message)

    client = TestClient(app)

    auth = client.post("/v1/auth/device")
    assert auth.status_code == 200
    token = auth.json()["api_token"]
    headers = {"Authorization": f"Bearer {token}"}

    link = client.post("/v1/telegram/link-code", headers=headers)
    assert link.status_code == 200
    code = link.json()["code"]

    webhook_headers = {}
    if settings.telegram_webhook_secret:
        webhook_headers["X-Telegram-Bot-Api-Secret-Token"] = settings.telegram_webhook_secret

    link_update = {
        "message": {
            "text": f"/link {code}",
            "chat": {"id": 12345},
            "from": {"id": 777},
        }
    }
    webhook = client.post("/v1/telegram/webhook", json=link_update, headers=webhook_headers)
    assert webhook.status_code == 200
    assert webhook.json()["status"] == "ok"

    ingest_payload = {
        "date": str(date.today()),
        "timezone": "Asia/Baku",
        "steps": 5000,
        "active_kcal": float(Decimal("260")),
        "sleep_min": 400,
        "sleep_start": None,
        "sleep_end": None,
        "resting_hr": None,
        "hrv_sdnn": None,
        "workouts_count": 1,
    }
    ingest = client.post("/v1/health/daily", json=ingest_payload, headers=headers)
    assert ingest.status_code == 200
    assert ingest.json()["status"] == "ok"

    today_update = {
        "message": {
            "text": "/today",
            "chat": {"id": 12345},
            "from": {"id": 777},
        }
    }
    today = client.post("/v1/telegram/webhook", json=today_update, headers=webhook_headers)
    assert today.status_code == 200
    assert today.json()["status"] == "ok"

    status = client.get("/v1/reports/status", headers=headers)
    assert status.status_code == 200
    assert status.json()["is_linked"] is True
