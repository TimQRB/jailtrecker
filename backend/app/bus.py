"""Redis Pub/Sub шина для real-time событий (канал jailtracker:events)."""
import json
from typing import Any

import redis.asyncio as aioredis

from .config import settings

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def publish_event(event_type: str, payload: dict[str, Any]) -> None:
    r = get_redis()
    message = json.dumps({"type": event_type, "payload": payload}, default=str)
    await r.publish(settings.events_channel, message)


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
