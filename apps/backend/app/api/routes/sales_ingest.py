from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.sales import IngestResponse, SalesSnapshotIn
from app.services.sales_ingest import upsert_sales_snapshot

router = APIRouter(prefix="/v1/sales", tags=["sales"])


@router.post("/snapshot", response_model=IngestResponse)
def ingest_sales_snapshot(
    payload: SalesSnapshotIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IngestResponse:
    upsert_sales_snapshot(db, current_user, payload)
    return IngestResponse(status="ok")
