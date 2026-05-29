"""
Симулятор GPS трекера DDX04 (протокол Xexun).

Отправляет данные на сервер по TCP для тестирования серверного ПО
без использования реального устройства.
"""

import socket
import time
import random
import logging
import argparse
import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# ─── Параметры из .env (со значениями по умолчанию) ──────────────────────────
IMEI = os.getenv("IMEI", "123456789012345")
PHONE = os.getenv("PHONE", "+77001234567")
SERVER_HOST = os.getenv("SERVER_HOST", "gw.flespi.io")
SERVER_PORT = int(os.getenv("SERVER_PORT", "20712"))
INTERVAL = int(os.getenv("INTERVAL", "60"))

START_LAT = float(os.getenv("START_LAT", "54.8645"))
START_LON = float(os.getenv("START_LON", "69.1386"))

GEOFENCE_LAT = float(os.getenv("GEOFENCE_LAT", "54.8645"))
GEOFENCE_LON = float(os.getenv("GEOFENCE_LON", "69.1386"))
GEOFENCE_RADIUS = float(os.getenv("GEOFENCE_RADIUS", "0.002"))
GEOFENCE_BREACH_AFTER = int(os.getenv("GEOFENCE_BREACH_AFTER", "5"))

# ─── Логирование ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("simulator")

# ─── Список цепочек вышек (LBS) для правдоподобия ───────────────────────────
LBS_CELLS = [
    "04D8:01D4:7139",
    "04D8:01D4:7140",
    "04D8:01D5:2A1B",
    "04D8:01D3:8F4C",
    "04D8:01D4:6E2F",
]


def _signal_label(level: int) -> str:
    """Человеческий статус сигнала."""
    if level >= 4:
        return "OK"
    if level >= 2:
        return "WEAK"
    return "NO"


def _rssi(level: int) -> str:
    """Уровень сигнала для протокола (0–5)."""
    return str(min(max(level, 0), 5))


# ═════════════════════════════════════════════════════════════════════════════
#  PacketBuilder
# ═════════════════════════════════════════════════════════════════════════════

class PacketBuilder:
    """Формирует строки пакетов в формате Xexun."""

    @staticmethod
    def _lat_to_xexun(lat: float) -> str:
        """54.8645 → 5451.8700 (DDMM.MMMM)."""
        deg = int(abs(lat))
        minutes = (abs(lat) - deg) * 60
        return f"{deg:02d}{minutes:07.4f}"

    @staticmethod
    def _lon_to_xexun(lon: float) -> str:
        """69.1386 → 06908.3160 (DDDMM.MMMM)."""
        deg = int(abs(lon))
        minutes = (abs(lon) - deg) * 60
        return f"{deg:03d}{minutes:07.4f}"

    @staticmethod
    def _ns(lat: float) -> str:
        return "N" if lat >= 0 else "S"

    @staticmethod
    def _ew(lon: float) -> str:
        return "E" if lon >= 0 else "W"

    @staticmethod
    def _now_tuple() -> tuple:
        """(yyMMddHHmm, HHmmss.SSS, ddMMyy) для текущего UTC."""
        now = datetime.now(timezone.utc)
        ts1 = now.strftime("%y%m%d%H%M")
        gps_time = now.strftime("%H%M%S") + ".000"
        date = now.strftime("%d%m%y")
        return ts1, gps_time, date

    @classmethod
    def _lbs(cls) -> str:
        """Случайная LBS строка."""
        return f"2501|{random.choice(LBS_CELLS)}|"

    @classmethod
    def _base(cls, imei: str, pkt_type: str, lat: float, lon: float,
              speed: float, course: float, fix: str, valid: str,
              battery: int, signal: int) -> str:
        ts1, gps_time, date = cls._now_tuple()
        lat_str = cls._lat_to_xexun(lat)
        lon_str = cls._lon_to_xexun(lon)
        ns = cls._ns(lat)
        ew = cls._ew(lon)

        return (
            f"imei:{imei},{pkt_type},{ts1},{PHONE},{fix},{gps_time},{valid},"
            f"{lat_str},{ns},{lon_str},{ew},{speed:.2f},{course:.2f},{date},,,"
            f"{battery}|{_rssi(signal)}|{cls._lbs()};"
        )

    @classmethod
    def gps(cls, imei: str, lat: float, lon: float, speed: float = 0.0,
            course: float = 0.0, battery: int = 85, signal: int = 4) -> str:
        return cls._base(imei, "tracker", lat, lon, speed, course,
                         "F", "A", battery, signal)

    @classmethod
    def sos(cls, imei: str, lat: float, lon: float) -> str:
        return cls._base(imei, "help me", lat, lon, 0.0, 0.0,
                         "F", "A", 85, 4)

    @classmethod
    def low_battery(cls, imei: str, lat: float, lon: float,
                    battery: int = 5, signal: int = 4) -> str:
        return cls._base(imei, "low battery", lat, lon, 0.0, 0.0,
                         "F", "A", battery, signal)

    @classmethod
    def no_signal(cls, imei: str, lat: float, lon: float,
                  battery: int = 85, signal: int = 0) -> str:
        return cls._base(imei, "tracker", lat, lon, 0.0, 0.0,
                         "L", "V", battery, signal)


# ═════════════════════════════════════════════════════════════════════════════
#  XexunSimulator
# ═════════════════════════════════════════════════════════════════════════════

class XexunSimulator:
    """Подключается к серверу по TCP, симулирует движение и отправляет пакеты."""

    def __init__(self):
        self.sock: socket.socket | None = None
        self.lat = START_LAT
        self.lon = START_LON
        self.speed = 0.0
        self.course = 0.0
        self.battery = 85
        self.signal = 4
        self.packet_count = 0

    # ── Управление соединением ───────────────────────────────────────────────

    def connect(self) -> None:
        """Подключение к серверу с авто-retry каждые 10 секунд."""
        while True:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(30)
                self.sock.connect((SERVER_HOST, SERVER_PORT))
                log.info("Подключено к %s:%s", SERVER_HOST, SERVER_PORT)
                return
            except (socket.timeout, ConnectionRefusedError, OSError) as exc:
                log.error("Ошибка подключения: %s. Повтор через 10 с…", exc)
                time.sleep(10)

    def disconnect(self) -> None:
        """Безопасное отключение."""
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None
        log.info("Отключено от сервера")

    def send(self, packet: str) -> None:
        """Отправка пакета; при ошибке — переподключение и повторная отправка."""
        if self.sock is None:
            self.connect()
        try:
            data = (packet + "\r\n").encode("utf-8")
            self.sock.sendall(data)
        except (BrokenPipeError, ConnectionResetError, OSError) as exc:
            log.error("Ошибка отправки: %s. Переподключение…", exc)
            self.disconnect()
            self.connect()
            self.sock.sendall((packet + "\r\n").encode("utf-8"))

    # ── Симуляция движения ───────────────────────────────────────────────────

    def move(self) -> None:
        """Плавное случайное смещение координат (имитация движения)."""
        self.lat += random.uniform(-0.0005, 0.0005)
        self.lon += random.uniform(-0.0005, 0.0005)
        self.speed = random.uniform(0.0, 5.0)
        self.course = random.uniform(0.0, 360.0)

    def breach_geofence(self) -> None:
        """Резкое смещение за пределы геофенса."""
        self.lat += random.uniform(0.01, 0.03) * random.choice([-1, 1])
        self.lon += random.uniform(0.01, 0.03) * random.choice([-1, 1])

    def is_inside_geofence(self) -> bool:
        """Проверка: находится ли точка внутри геофенса."""
        dlat = self.lat - GEOFENCE_LAT
        dlon = self.lon - GEOFENCE_LON
        return (dlat * dlat + dlon * dlon) ** 0.5 <= GEOFENCE_RADIUS

    # ── Отправка пакетов ─────────────────────────────────────────────────────

    def send_gps(self) -> None:
        """Сформировать и отправить GPS-пакет."""
        packet = PacketBuilder.gps(
            IMEI, self.lat, self.lon, self.speed, self.course,
            self.battery, self.signal,
        )
        inside = self.is_inside_geofence()
        suffix = ""
        if not inside and self.packet_count > 1:
            suffix = " — ВЫШЕЛ ЗА ГЕОФЕНС"
        self.send(packet)
        log.info(
            "[GPS]     lat=%.4f lon=%.4f speed=%.1f battery=%d%% signal=%s%s",
            self.lat, self.lon, self.speed, self.battery,
            _signal_label(self.signal), suffix,
        )

    def send_sos(self) -> None:
        """Сформировать и отправить SOS-пакет."""
        packet = PacketBuilder.sos(IMEI, self.lat, self.lon)
        self.send(packet)
        log.info("[SOS]     lat=%.4f lon=%.4f ТРЕВОГА!", self.lat, self.lon)

    def send_low_battery(self) -> None:
        """Сформировать и отправить пакет низкого заряда."""
        packet = PacketBuilder.low_battery(IMEI, self.lat, self.lon, battery=5)
        self.send(packet)
        log.info(
            "[BATTERY] lat=%.4f lon=%.4f battery=%d%% — низкий заряд",
            self.lat, self.lon, self.battery,
        )

    def send_no_signal(self) -> None:
        """Сформировать и отправить пакет без GPS-сигнала."""
        packet = PacketBuilder.no_signal(IMEI, self.lat, self.lon, signal=0)
        self.send(packet)
        log.info(
            "[NO GPS]  lat=%.4f lon=%.4f signal=%s — нет сигнала",
            self.lat, self.lon, _signal_label(0),
        )

    # ── Сценарии ─────────────────────────────────────────────────────────────

    def run_scenario(self, mode: str) -> None:
        """Запустить выбранный сценарий."""
        self.connect()
        self.packet_count = 0
        geofence_breached = False
        battery_sent = False

        log.info("Сценарий: %s | IMEI: %s | Интервал: %d с", mode, IMEI, INTERVAL)

        try:
            while True:
                self.packet_count += 1
                self.move()

                # ── geofence: выход за зону после N пакетов ──
                if mode == "geofence" and not geofence_breached \
                        and self.packet_count > GEOFENCE_BREACH_AFTER:
                    self.breach_geofence()
                    geofence_breached = True

                # ── sos: тревога на 3-м пакете ──
                if mode == "sos" and self.packet_count == 3:
                    self.send_sos()
                    self.send_gps()

                # ── offline: обрыв связи на 3-м пакете ──
                elif mode == "offline" and self.packet_count == 3:
                    self.send_gps()
                    log.info("[OFFLINE] Имитация обрыва связи")
                    self.disconnect()
                    break

                # ── normal / по умолчанию ──
                else:
                    self.send_gps()

                # Дополнительно: раз в 10 пакетов — low battery
                if mode != "offline" and self.packet_count % 10 == 0 and not battery_sent:
                    if random.random() < 0.3:
                        self.send_low_battery()
                        battery_sent = True

                time.sleep(INTERVAL)

        except KeyboardInterrupt:
            log.info("Остановка по Ctrl+C")
        finally:
            self.disconnect()


# ═════════════════════════════════════════════════════════════════════════════
#  Точка входа
# ═════════════════════════════════════════════════════════════════════════════

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Симулятор GPS трекера DDX04 (протокол Xexun)",
    )
    parser.add_argument(
        "--mode", choices=["normal", "sos", "geofence", "offline"],
        default="normal", help="Режим работы симулятора",
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Отправить один пакет каждого типа и выйти",
    )
    return parser.parse_args(argv)


def demo_once() -> None:
    """Отправить по одному пакету каждого типа для проверки."""
    sim = XexunSimulator()
    sim.connect()
    sim.send_gps()
    time.sleep(1)
    sim.send_sos()
    time.sleep(1)
    sim.send_low_battery()
    time.sleep(1)
    sim.send_no_signal()
    sim.disconnect()


def main() -> None:
    args = parse_args()
    if args.once:
        demo_once()
        return
    sim = XexunSimulator()
    sim.run_scenario(args.mode)


if __name__ == "__main__":
    main()
