"""Точка входа FastAPI: lifespan, CORS, роутеры, Redis-listener."""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .bus import close_redis
from .config import settings
from .init_db import seed_admin
from .routers import (
    audit,
    auth,
    cases,
    devices,
    geofences,
    health,
    incidents,
    inmates,
    locations,
    schedules,
    users,
    ws,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jailtracker")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # сидируем демо-админа (схему накатывает Alembic, не create_all)
    seed_admin()
    listener_task = asyncio.create_task(ws.redis_listener())
    logger.info("jailtracker backend started")
    try:
        yield
    finally:
        listener_task.cancel()
        await close_redis()


app = FastAPI(title="jailtracker API", version="0.1.0", lifespan=lifespan)

# Security-фикс SafeMektep #7: CORS НЕ "*", а явный белый список из env.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (
    auth,
    users,
    inmates,
    cases,
    devices,
    geofences,
    schedules,
    locations,
    incidents,
    audit,
    health,
    ws,
):
    app.include_router(module.router)


@app.get("/")
def root():
    return {"service": "jailtracker", "docs": "/docs"}
