"""Минимальный кодек кадров HC02 (бинарный протокол 0x4050).

Скелет под перенос из SafeMektep. Реальные коды P_* и парсинг полей берутся из
вендорской спеки (AT-commands / ARCHITECTURE .docx в референсном проекте).
Здесь — каркас: магия кадра, тип протокола, контрольная сумма.
"""
import struct

FRAME_MAGIC = 0x4050

# Типы протокола (P_*) — расширяются по мере переноса из спеки.
P_REGISTER = 0x01
P_POSITION = 0x02
P_HEARTBEAT = 0x03
P_TAMPER = 0x04        # вскрытие/срез ремня
P_COMMAND = 0x80       # команда серверу->устройству
P_REMOTE_AT = 0x10FF   # удалённый AT (как в SafeMektep)


def checksum(payload: bytes) -> int:
    s = 0
    for b in payload:
        s = (s + b) & 0xFFFF
    return s


def encode_frame(ptype: int, payload: bytes) -> bytes:
    header = struct.pack(">HHH", FRAME_MAGIC, ptype, len(payload))
    return header + payload + struct.pack(">H", checksum(payload))


def decode_frame(buf: bytes) -> tuple[int, bytes, bytes] | None:
    """Возвращает (ptype, payload, остаток) либо None, если кадр ещё не дочитан."""
    if len(buf) < 6:
        return None
    magic, ptype, length = struct.unpack(">HHH", buf[:6])
    if magic != FRAME_MAGIC:
        raise ValueError("bad frame magic")
    end = 6 + length + 2
    if len(buf) < end:
        return None
    payload = buf[6 : 6 + length]
    return ptype, payload, buf[end:]
