from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.health_ingest import router as health_ingest_router
from app.api.routes.insights_route import router as insights_router
from app.api.routes.internal import router as internal_router
from app.api.routes.profile_route import router as profile_router
from app.api.routes.reports import router as reports_router
from app.api.routes.sales_ingest import router as sales_ingest_router
from app.api.routes.telegram import router as telegram_router
from app.api.routes.usage_route import router as usage_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(telegram_router)
api_router.include_router(health_ingest_router)
api_router.include_router(sales_ingest_router)
api_router.include_router(reports_router)
api_router.include_router(profile_router)
api_router.include_router(insights_router)
api_router.include_router(usage_router)
api_router.include_router(internal_router)
