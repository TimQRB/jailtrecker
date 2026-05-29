"""Приём локаций от источника (симулятор/HTTP) + треки.

POST /api/ingest/location аутентифицируется по X-API-Key устройства.
Закрыт known issue SafeMektep #6: на ingest стоит rate-limit (Redis sliding counter).
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..bus import get_redis, publish_event
from ..config import settings
from ..database import get_db
from ..geofence_service import evaluate_point
from ..models import (
    Device,
    Incident,
    IncidentType,
    LocationPoint,
    Severity,
    TamperState,
    User,
    UserRole,
)
from ..schemas import LocationIngest, LocationOut
from ..security import require_roles

router = APIRouter(tags=["locations"])
admin_only = require_roles(UserRole.admin)

LOW_BATTERY_THRESHOLD = 15


async def _check_rate_limit(api_key: str) -> None:
    """Скользящее окно в 60с на ключ устройства."""
    r = get_redis()
    bucket = f"ratelimit:ingest:{api_key}"
    count = await r.incr(bucket)
    if count == 1:
        await r.expire(bucket, 60)
    if count > settings.ingest_rate_limit_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Превышен лимит частоты ingest",
        )


@router.post("/api/ingest/location", response_model=LocationOut, status_code=status.HTTP_201_CREATED)
async def ingest_location(
    body: LocationIngest,
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
):
    device = db.scalar(select(Device).where(Device.imei == body.imei))
    if device is None or device.api_key != x_api_key or not device.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный ключ устройства")

    await _check_rate_limit(device.api_key)

    recorded_at = body.recorded_at or datetime.now(timezone.utc)
    point = LocationPoint(
        device_id=device.id,
        lat=body.lat,
        lon=body.lon,
        accuracy=body.accuracy,
        speed=body.speed,
        battery=body.battery,
        source="http",
        recorded_at=recorded_at,
    )
    db.add(point)

    device.last_seen_at = recorded_at
    if body.battery is not None:
        device.last_battery = body.battery

    incidents: list[Incident] = []

    # tamper-detection браслета — критический алерт
    if body.tamper is not None and body.tamper != TamperState.ok and device.tamper_state != body.tamper:
        device.tamper_state = body.tamper
        incidents.append(
            Incident(
                inmate_id=device.inmate_id,
                device_id=device.id,
                incident_type=IncidentType.tamper,
                severity=Severity.critical,
                message=(
                    "Срез ремня браслета" if body.tamper == TamperState.strap_cut else "Вскрытие корпуса браслета"
                ),
                lat=body.lat,
                lon=body.lon,
            )
        )

    # низкий заряд
    if body.battery is not None and body.battery <= LOW_BATTERY_THRESHOLD:
        incidents.append(
            Incident(
                inmate_id=device.inmate_id,
                device_id=device.id,
                incident_type=IncidentType.low_battery,
                severity=Severity.warning,
                message=f"Низкий заряд браслета: {body.battery}%",
                lat=body.lat,
                lon=body.lon,
            )
        )

    # геозоны + комендантский час
    incidents.extend(evaluate_point(db, device, body.lat, body.lon))

    db.commit()
    db.refresh(point)
    for inc in incidents:
        db.refresh(inc)

    # real-time публикация в WebSocket-клиентов
    await publish_event(
        "location",
        {
            "device_id": device.id,
            "inmate_id": device.inmate_id,
            "lat": body.lat,
            "lon": body.lon,
            "battery": body.battery,
            "recorded_at": recorded_at,
        },
    )
    for inc in incidents:
        await publish_event(
            "incident",
            {
                "id": inc.id,
                "inmate_id": inc.inmate_id,
                "incident_type": inc.incident_type.value,
                "severity": inc.severity.value,
                "message": inc.message,
                "lat": inc.lat,
                "lon": inc.lon,
                "created_at": inc.created_at,
            },
        )

    return point


@router.get("/api/inmates/{inmate_id}/track", response_model=list[LocationOut])
def inmate_track(
    inmate_id: int,
    limit: int = 200,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    device = db.scalar(select(Device).where(Device.inmate_id == inmate_id))
    if device is None:
        return []
    return db.scalars(
        select(LocationPoint)
        .where(LocationPoint.device_id == device.id)
        .order_by(LocationPoint.recorded_at.desc())
        .limit(min(limit, 1000))
    ).all()


@router.get("/api/inmates/{inmate_id}/last-location", response_model=LocationOut | None)
def inmate_last_location(
    inmate_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    device = db.scalar(select(Device).where(Device.inmate_id == inmate_id))
    if device is None:
        return None
    return db.scalar(
        select(LocationPoint)
        .where(LocationPoint.device_id == device.id)
        .order_by(LocationPoint.recorded_at.desc())
        .limit(1)
    )
