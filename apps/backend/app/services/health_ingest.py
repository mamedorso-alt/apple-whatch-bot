from sqlalchemy.orm import Session

from app.db.models import DailyMetric, User
from app.schemas.health import DailyMetricsIn
from app.services.scoring import upsert_daily_score


def upsert_daily_metrics(db: Session, user: User, payload: DailyMetricsIn) -> DailyMetric:
    row = db.query(DailyMetric).filter(DailyMetric.user_id == user.id, DailyMetric.date == payload.date).first()
    if row is None:
        row = DailyMetric(user_id=user.id, date=payload.date)
        db.add(row)

    row.steps = payload.steps
    row.active_kcal = payload.active_kcal
    row.sleep_min = payload.sleep_min
    row.sleep_start = payload.sleep_start
    row.sleep_end = payload.sleep_end
    row.resting_hr = payload.resting_hr
    row.hrv_sdnn = payload.hrv_sdnn
    row.workouts_count = payload.workouts_count

    db.commit()
    db.refresh(row)
    upsert_daily_score(db, row)
    return row
