"""HTTP-симулятор браслета: шлёт локации на /api/ingest/location с X-API-Key.

Использование:
    python simulate.py --api-key <API_KEY> --imei <IMEI>

Интерактивные команды в терминале:
    w — пройтись (сдвинуть точку)
    b — посадить батарею до 8%
    t — сымитировать срез ремня (tamper=strap_cut)
    o — вернуть tamper в ok
    q — выход
"""
import argparse
import threading
import time

import requests

state = {
    "lat": 51.165,
    "lon": 71.460,
    "battery": 95,
    "tamper": "ok",
    "running": True,
}


def sender(base_url: str, api_key: str, imei: str, interval: float) -> None:
    while state["running"]:
        body = {
            "imei": imei,
            "lat": state["lat"],
            "lon": state["lon"],
            "battery": state["battery"],
            "tamper": state["tamper"],
        }
        try:
            r = requests.post(
                f"{base_url}/api/ingest/location",
                json=body,
                headers={"X-API-Key": api_key},
                timeout=5,
            )
            print(f"[{r.status_code}] lat={state['lat']:.5f} lon={state['lon']:.5f} "
                  f"batt={state['battery']} tamper={state['tamper']}")
        except Exception as exc:  # noqa: BLE001
            print("Ошибка отправки:", exc)
        time.sleep(interval)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8080")
    ap.add_argument("--api-key", required=True)
    ap.add_argument("--imei", required=True)
    ap.add_argument("--interval", type=float, default=5.0)
    args = ap.parse_args()

    t = threading.Thread(
        target=sender, args=(args.base_url, args.api_key, args.imei, args.interval), daemon=True
    )
    t.start()

    print("Команды: w — шаг, b — низкий заряд, t — срез ремня, o — tamper ok, q — выход")
    while True:
        cmd = input("> ").strip().lower()
        if cmd == "w":
            state["lat"] += 0.001
            state["lon"] += 0.001
        elif cmd == "b":
            state["battery"] = 8
        elif cmd == "t":
            state["tamper"] = "strap_cut"
        elif cmd == "o":
            state["tamper"] = "ok"
        elif cmd == "q":
            state["running"] = False
            break


if __name__ == "__main__":
    main()
