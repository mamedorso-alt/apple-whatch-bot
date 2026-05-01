from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.services.scheduler import run_scheduled_reports

router = APIRouter(prefix="/internal", tags=["internal"])
settings = get_settings()


@router.post("/run-scheduled")
async def run_scheduled(
    x_internal_secret: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    if settings.jwt_secret and x_internal_secret != settings.jwt_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal secret")
    return await run_scheduled_reports(db)
