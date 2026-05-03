from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.reels_schedule import run_reels_agent_scheduled
from app.services.scheduler import run_scheduled_reports

scheduler = AsyncIOScheduler()


async def _run_tick() -> None:
    s = get_settings()
    db = SessionLocal()
    try:
        if s.scheduler_enabled:
            await run_scheduled_reports(db)
        await run_reels_agent_scheduled(db)
    finally:
        db.close()


def start_scheduler() -> None:
    s = get_settings()
    if not s.scheduler_enabled and not s.reels_agent_enabled:
        return
    if scheduler.running:
        return
    interval = max(1, s.scheduler_interval_min)
    scheduler.add_job(_run_tick, "interval", minutes=interval, id="scheduled-reports", replace_existing=True)
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
