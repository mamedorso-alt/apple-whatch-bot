from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.usage import AgentSpendResponse
from app.services.agent_usage import sum_spend_usd

router = APIRouter(prefix="/v1/usage", tags=["usage"])


@router.get("/spend", response_model=AgentSpendResponse)
def get_agent_spend(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AgentSpendResponse:
    totals = sum_spend_usd(db, current_user)
    return AgentSpendResponse(
        currency="USD",
        day_usd=float(totals["day_usd"]),
        week_usd=float(totals["week_usd"]),
        month_usd=float(totals["month_usd"]),
    )
