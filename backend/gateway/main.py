"""TCP Gateway для браслетов HC02.

Отдельный процесс, общий код с API (./backend). Слушает :13000 (регистрация)
и :13001 (сервис). При коннекте устройства вычитывает накопленную очередь команд
из Redis (dev_cmd_queue:<IMEI>) — закрывает known issue SafeMektep #2.

Это рабочий каркас: разбор позиции/tamper из payload реализуется по вендорской спеке.
"""
import asyncio
import json
import logging

from app.bus import get_redis
from app.config import settings
from app.device_commands import drain_queue

from .protocol import P_POSITION, P_REGISTER, P_TAMPER, decode_frame

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jailtracker.gateway")

REG_PORT = 13000
SVC_PORT = 13001


async def _deliver_queued_commands(imei: str, writer: asyncio.StreamWriter) -> None:
    commands = await drain_queue(imei)
    for cmd in commands:
        logger.info("→ %s: %s", imei, cmd)
        # TODO: сериализовать команду в кадр протокола и отправить устройству
        # writer.write(encode_frame(P_COMMAND, ...)); await writer.drain()


async def handle_connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    peer = writer.get_extra_info("peername")
    logger.info("Подключение устройства: %s", peer)
    buf = b""
    imei: str | None = None
    try:
        while True:
            chunk = await reader.read(4096)
            if not chunk:
                break
            buf += chunk
            while True:
                decoded = decode_frame(buf)
                if decoded is None:
                    break
                ptype, payload, buf = decoded
                if ptype == P_REGISTER:
                    imei = payload.decode(errors="ignore").strip()
                    logger.info("Регистрация IMEI=%s", imei)
                    await _deliver_queued_commands(imei, writer)
                elif ptype == P_POSITION:
                    # TODO: распарсить lat/lon/battery по спеке и отправить в API/БД
                    logger.info("Позиция от %s (%d байт)", imei, len(payload))
                elif ptype == P_TAMPER:
                    logger.warning("TAMPER от %s", imei)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ошибка соединения %s: %s", peer, exc)
    finally:
        writer.close()


async def main() -> None:
    # прогреваем Redis-соединение
    get_redis()
    reg_server = await asyncio.start_server(handle_connection, "0.0.0.0", REG_PORT)
    svc_server = await asyncio.start_server(handle_connection, "0.0.0.0", SVC_PORT)
    logger.info("Gateway слушает :%d (reg) и :%d (svc)", REG_PORT, SVC_PORT)
    async with reg_server, svc_server:
        await asyncio.gather(reg_server.serve_forever(), svc_server.serve_forever())


if __name__ == "__main__":
    asyncio.run(main())
