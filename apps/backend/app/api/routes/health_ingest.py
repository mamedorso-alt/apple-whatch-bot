from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.health import DailyMetricsIn, IngestResponse
from app.services.health_ingest import upsert_daily_metrics

router = APIRouter(prefix="/v1/health", tags=["health"])


@router.post("/daily", response_model=IngestResponse)
def ingest_daily(
    payload: DailyMetricsIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IngestResponse:
    upsert_daily_metrics(db, current_user, payload)
    return IngestResponse(status="ok")
