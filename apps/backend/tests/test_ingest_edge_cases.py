from datetime import date
from decimal import Decimal

from app.schemas.health import DailyMetricsIn
from app.services.health_ingest import upsert_daily_metrics
from tests.conftest import FakeSession, make_user


def test_ingest_partial_data_no_crash():
    db = FakeSession()
    user = make_user(language="ru")
    db.users.append(user)

    payload = DailyMetricsIn(
        date=date.today(),
        timezone="Asia/Baku",
        steps=1500,
        active_kcal=Decimal("120"),
        sleep_min=0,
        sleep_start=None,
        sleep_end=None,
        resting_hr=None,
        hrv_sdnn=None,
        workouts_count=0,
    )

    metric = upsert_daily_metrics(db, user, payload)

    assert metric.steps == 1500
    assert metric.hrv_sdnn is None
    assert metric.resting_hr is None
    assert len(db.daily_scores) == 1
