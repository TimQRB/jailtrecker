"""WebSocket для real-time локаций и инцидентов.

Security-фикс SafeMektep #5: JWT НЕ передаётся в query-строке (попадал в логи прокси).
Вместо этого клиент после установления соединения шлёт первым сообщением
{"type": "auth", "token": "<JWT>"} — токен не светится в URL.
"""
import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..bus import get_redis
from ..config import settings
from ..security import decode_token

router = APIRouter(tags=["ws"])

AUTH_TIMEOUT_SEC = 5


class ConnectionManager:
    def __init__(self) -> None:
        self.active: set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        self.active.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self.active.discard(ws)

    async def broadcast(self, message: str) -> None:
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


async def _authenticate(ws: WebSocket) -> bool:
    try:
        raw = await asyncio.wait_for(ws.receive_text(), timeout=AUTH_TIMEOUT_SEC)
        msg = json.loads(raw)
        if msg.get("type") != "auth":
            return False
        decode_token(msg["token"])
        return True
    except Exception:
        return False


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    if not await _authenticate(ws):
        await ws.close(code=4401)  # unauthorized
        return

    await manager.connect(ws)
    await ws.send_text(json.dumps({"type": "ready"}))
    try:
        while True:
            # держим соединение; входящие пинги игнорируем
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)


async def redis_listener() -> None:
    """Слушает канал событий и фанит локальным WS-клиентам. Запускается в lifespan."""
    r = get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(settings.events_channel)
    async for message in pubsub.listen():
        if message["type"] != "message":
            continue
        await manager.broadcast(message["data"])
