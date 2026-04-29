from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.services.worker import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(_app: FastAPI):
    start_scheduler()
    try:
        yield
    finally:
        stop_scheduler()


app = FastAPI(title="Productivity Assistant API", version="0.1.0", lifespan=lifespan)
app.include_router(api_router)
