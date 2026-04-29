from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import DailyMetric, DailyScore, User
from app.db.session import get_db
from app.services.reports import compose_today_report, compose_week_report

router = APIRouter(prefix="/v1/reports", tags=["reports"])


@router.get("/today")
def get_today_report(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    today = datetime.now(timezone.utc).date()
    report = compose_today_report(db, current_user, today)
    return {"date": str(today), "report": report}


@router.get("/week")
def get_week_report(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    today = datetime.now(timezone.utc).date()
    report = compose_week_report(db, current_user, today)
    return {"end_date": str(today), "report": report}


@router.get("/status")
def get_report_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str | bool | None]:
    today = datetime.now(timezone.utc).date()
    latest_metric = (
        db.query(DailyMetric)
        .filter(DailyMetric.user_id == current_user.id)
        .order_by(DailyMetric.date.desc())
        .first()
    )
    today_score = (
        db.query(DailyScore)
        .filter(DailyScore.user_id == current_user.id, DailyScore.date == today)
        .first()
    )
    return {
        "is_linked": current_user.is_linked,
        "language": current_user.language,
        "timezone": current_user.timezone,
        "last_sync_date": str(latest_metric.date) if latest_metric else None,
        "has_today_score": today_score is not None,
    }
