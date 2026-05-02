from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.reels_schedule import run_reels_agent_scheduled
from app.services.scheduler import run_scheduled_reports

settings = get_settings()
scheduler = AsyncIOScheduler()


async def _run_tick() -> None:
    db = SessionLocal()
    try:
        await run_scheduled_reports(db)
        await run_reels_agent_scheduled(db)
    finally:
        db.close()


def start_scheduler() -> None:
    if not settings.scheduler_enabled:
        return
    if scheduler.running:
        return
    scheduler.add_job(_run_tick, "interval", minutes=max(1, settings.scheduler_interval_min), id="scheduled-reports", replace_existing=True)
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
