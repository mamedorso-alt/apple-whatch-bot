from datetime import date, timedelta
from decimal import Decimal

from app.services.scoring import calculate_daily_score
from tests.conftest import FakeSession, make_metric


def test_scoring_penalties_and_mode():
    db = FakeSession()
    today = date.today()

    # baseline history
    for idx in range(1, 6):
        db.daily_metrics.append(
            make_metric(
                user_id="u1",
                day=today - timedelta(days=idx),
                sleep_min=430,
                steps=9000,
                active_kcal=280,
            )
        )

    metric = make_metric(user_id="u1", day=today, sleep_min=320, steps=2000, active_kcal=Decimal("100"))
    metric.resting_hr = Decimal("80")
    metric.hrv_sdnn = Decimal("20")

    score, mode, reasons = calculate_daily_score(db, metric)

    assert score < 45
    assert mode == "recovery"
    assert "sleep_low" in reasons["items"]
    assert "steps_low" in reasons["items"]
