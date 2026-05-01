from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.services.insights import build_daily_insight_text, build_weekly_trend_text

router = APIRouter(prefix="/v1/insights", tags=["insights"])


@router.get("/daily")
def insights_daily(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    day: date | None = None,
) -> dict[str, str]:
    today = day or datetime.now(timezone.utc).date()
    text = build_daily_insight_text(db, current_user, today, current_user.language)
    return {"text": text, "date": str(today)}


@router.get("/weekly")
def insights_weekly(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    day: date | None = None,
) -> dict[str, str]:
    today = day or datetime.now(timezone.utc).date()
    text = build_weekly_trend_text(db, current_user, today, current_user.language)
    return {"text": text, "week_end": str(today)}
