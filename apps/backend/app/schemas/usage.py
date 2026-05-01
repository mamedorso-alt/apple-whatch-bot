from pydantic import BaseModel, Field


class AgentSpendResponse(BaseModel):
    currency: str = Field(default="USD")
    day_usd: float
    week_usd: float
    month_usd: float
