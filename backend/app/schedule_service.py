"""Логика комендантского часа / расписания.

В отличие от SafeMektep (known issue #3, lesson_mode не персистировался),
расписание хранится в БД и проверяется на каждой точке.
"""
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    Device,
    Incident,
    IncidentType,
    Schedule,
    ScheduleRule,
    Severity,
)


def _active_now(schedule: Schedule, now: datetime) -> bool:
    if not schedule.is_active:
        return False
    if schedule.day_of_week is not None and schedule.day_of_week != now.weekday():
        return False
    t = now.time()
    start, end = schedule.start_time, schedule.end_time
    if start <= end:
        return start <= t <= end
    # интервал через полночь (напр. 22:00–06:00)
    return t >= start or t <= end


def is_curfew_now(
    db: Session,
    device: Device,
    lat: float,
    lon: float,
    point_inside: Callable[[Session, int, float, float], bool],
) -> Incident | None:
    """Если действует правило must_be_inside и точка вне требуемой зоны — вернуть инцидент."""
    if device.inmate_id is None:
        return None

    now = datetime.now(timezone.utc)
    schedules = db.scalars(
        select(Schedule).where(
            Schedule.inmate_id == device.inmate_id,
            Schedule.rule == ScheduleRule.must_be_inside,
            Schedule.is_active.is_(True),
        )
    ).all()

    for sch in schedules:
        if not _active_now(sch, now):
            continue
        if not point_inside(db, sch.geofence_id, lat, lon):
            return Incident(
                inmate_id=device.inmate_id,
                device_id=device.id,
                incident_type=IncidentType.curfew_violation,
                severity=Severity.critical,
                geofence_id=sch.geofence_id,
                message="Нарушение комендантского часа: вне обязательной зоны",
                lat=lat,
                lon=lon,
            )
    return None
