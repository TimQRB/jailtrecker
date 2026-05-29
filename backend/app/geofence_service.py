"""Геозоны через PostGIS: построение полигонов, ST_Covers, детекция enter/exit
и формирование инцидентов нарушений с учётом типа зоны и расписания."""
from datetime import datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .models import (
    Device,
    DeviceZoneState,
    Geofence,
    Incident,
    IncidentType,
    Severity,
    ZoneType,
)
from .schedule_service import is_curfew_now


def coords_to_wkt(coordinates: list[list[float]]) -> str:
    """[[lon,lat], ...] -> POLYGON WKT (замыкает кольцо при необходимости)."""
    ring = list(coordinates)
    if ring[0] != ring[-1]:
        ring = ring + [ring[0]]
    pts = ", ".join(f"{lon} {lat}" for lon, lat in ring)
    return f"POLYGON(({pts}))"


def geom_to_coords(db: Session, geofence: Geofence) -> list[list[float]]:
    """Достаём кольцо координат полигона как [[lon,lat], ...]."""
    geojson = db.scalar(select(func.ST_AsGeoJSON(geofence.polygon)))
    if not geojson:
        return []
    import json

    data = json.loads(geojson)
    # POLYGON -> coordinates[0] = внешнее кольцо
    return [[pt[0], pt[1]] for pt in data["coordinates"][0]]


def _point_inside(db: Session, geofence_id: int, lat: float, lon: float) -> bool:
    sql = text(
        "SELECT ST_Covers(polygon, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)) "
        "FROM geofences WHERE id = :gid"
    )
    return bool(db.scalar(sql, {"lon": lon, "lat": lat, "gid": geofence_id}))


# Какие типы зон при ВЫХОДЕ дают инцидент (обязан быть внутри)
_EXIT_ALERTS = {ZoneType.home, ZoneType.perimeter, ZoneType.route_corridor}
# Какие типы зон при ВХОДЕ дают инцидент (запретные)
_ENTER_ALERTS = {ZoneType.forbidden}


def evaluate_point(
    db: Session, device: Device, lat: float, lon: float
) -> list[Incident]:
    """Пересчитать состояние зон для устройства по новой точке и создать инциденты.

    Возвращает список созданных (но ещё не закоммиченных) инцидентов.
    """
    incidents: list[Incident] = []

    # Зоны, релевантные устройству: общие (inmate_id IS NULL) + персональные.
    q = select(Geofence).where(Geofence.is_active.is_(True))
    if device.inmate_id is not None:
        q = q.where(
            (Geofence.inmate_id.is_(None)) | (Geofence.inmate_id == device.inmate_id)
        )
    else:
        q = q.where(Geofence.inmate_id.is_(None))
    geofences = db.scalars(q).all()

    for gf in geofences:
        inside = _point_inside(db, gf.id, lat, lon)

        state = db.scalar(
            select(DeviceZoneState).where(
                DeviceZoneState.device_id == device.id,
                DeviceZoneState.geofence_id == gf.id,
            )
        )
        prev_inside = state.is_inside if state else None

        if state is None:
            state = DeviceZoneState(device_id=device.id, geofence_id=gf.id, is_inside=inside)
            db.add(state)
        else:
            state.is_inside = inside
            state.updated_at = datetime.now(timezone.utc)

        # переход не зафиксирован — пропускаем формирование инцидента
        if prev_inside is None or prev_inside == inside:
            continue

        inc = None
        if not inside and gf.zone_type in _EXIT_ALERTS:
            itype = (
                IncidentType.route_deviation
                if gf.zone_type == ZoneType.route_corridor
                else IncidentType.exit_zone
            )
            inc = Incident(
                inmate_id=device.inmate_id,
                device_id=device.id,
                incident_type=itype,
                severity=Severity.critical,
                geofence_id=gf.id,
                message=f"Выход из зоны «{gf.name}» ({gf.zone_type.value})",
                lat=lat,
                lon=lon,
            )
        elif inside and gf.zone_type in _ENTER_ALERTS:
            inc = Incident(
                inmate_id=device.inmate_id,
                device_id=device.id,
                incident_type=IncidentType.enter_forbidden,
                severity=Severity.critical,
                geofence_id=gf.id,
                message=f"Вход в запретную зону «{gf.name}»",
                lat=lat,
                lon=lon,
            )

        if inc is not None:
            db.add(inc)
            incidents.append(inc)

    # Комендантский час: если сейчас «обязан быть внутри», а точка вне всех must_be_inside-зон.
    curfew_inc = is_curfew_now(db, device, lat, lon, _point_inside)
    if curfew_inc is not None:
        db.add(curfew_inc)
        incidents.append(curfew_inc)

    return incidents
