from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import AgentUsageEvent, User
from app.services.agent_usage import estimate_cost_usd, sum_spend_usd


def test_estimate_cost_anthropic_sonnet():
    c = estimate_cost_usd("anthropic", "claude-3-5-sonnet-latest", 1_000_000, 1_000_000)
    assert c == Decimal("3.0") + Decimal("15.0")


def test_sum_spend_respects_user_timezone_window():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = Session()

    uid = uuid4()
    user = User(
        id=uid,
        api_token_hash="a" * 64,
        timezone="UTC",
        language="en",
    )
    db.add(user)
    db.commit()

    now = datetime.now(timezone.utc)
    db.add(
        AgentUsageEvent(
            user_id=uid,
            provider="anthropic",
            model="claude",
            operation="coach_chat",
            input_tokens=0,
            output_tokens=0,
            cost_usd=Decimal("1.00"),
            created_at=now - timedelta(minutes=30),
        )
    )
    db.add(
        AgentUsageEvent(
            user_id=uid,
            provider="anthropic",
            model="claude",
            operation="coach_chat",
            input_tokens=0,
            output_tokens=0,
            cost_usd=Decimal("2.00"),
            created_at=now - timedelta(minutes=10),
        )
    )
    db.commit()

    totals = sum_spend_usd(db, user)
    assert totals["day_usd"] >= Decimal("1.00")
    assert totals["week_usd"] >= Decimal("1.00")
    assert totals["month_usd"] >= Decimal("3.00")

    db.close()
