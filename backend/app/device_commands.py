"""Отправка команд устройствам через Redis + персистентная очередь для offline.

Закрывает known issue SafeMektep #2: команды offline-устройствам не терялись.
Команда всегда складывается в Redis-список dev_cmd_queue:<IMEI> (durable, переживает
рестарт при включённом RDB/AOF) и дополнительно публикуется в канал dev_cmd:<IMEI>
для немедленной доставки, если gateway держит соединение.
"""
import json
from typing import Any

from .bus import get_redis
from .config import settings


def _channel(imei: str) -> str:
    return f"{settings.device_cmd_prefix}{imei}"


def _queue_key(imei: str) -> str:
    return f"dev_cmd_queue:{imei}"


async def send_command(imei: str, command: str, params: dict[str, Any] | None = None) -> None:
    r = get_redis()
    payload = json.dumps({"command": command, "params": params or {}}, default=str)
    # durable очередь — gateway вычитывает при коннекте устройства
    await r.rpush(_queue_key(imei), payload)
    # немедленная доставка, если устройство онлайн
    await r.publish(_channel(imei), payload)


async def drain_queue(imei: str) -> list[dict[str, Any]]:
    """Забрать все накопленные команды для устройства (вызывается gateway при коннекте)."""
    r = get_redis()
    key = _queue_key(imei)
    items = await r.lrange(key, 0, -1)
    if items:
        await r.delete(key)
    return [json.loads(i) for i in items]
