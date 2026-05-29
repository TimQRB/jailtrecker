"""CRUD геозон (PostGIS POLYGON)."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..audit import log_action
from ..database import get_db
from ..geofence_service import coords_to_wkt, geom_to_coords
from ..models import Geofence, User, UserRole
from ..schemas import GeofenceCreate, GeofenceOut, GeofenceUpdate
from ..security import require_roles

router = APIRouter(prefix="/api/geofences", tags=["geofences"])
admin_only = require_roles(UserRole.admin)


def _to_out(db: Session, gf: Geofence) -> GeofenceOut:
    return GeofenceOut(
        id=gf.id,
        name=gf.name,
        zone_type=gf.zone_type,
        coordinates=geom_to_coords(db, gf),
        inmate_id=gf.inmate_id,
        case_id=gf.case_id,
        is_active=gf.is_active,
        created_at=gf.created_at,
    )


@router.get("", response_model=list[GeofenceOut])
def list_geofences(
    inmate_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    q = select(Geofence).order_by(Geofence.id)
    if inmate_id is not None:
        q = q.where((Geofence.inmate_id == inmate_id) | (Geofence.inmate_id.is_(None)))
    return [_to_out(db, gf) for gf in db.scalars(q).all()]


@router.post("", response_model=GeofenceOut, status_code=status.HTTP_201_CREATED)
def create_geofence(
    body: GeofenceCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_only),
):
    wkt = coords_to_wkt(body.coordinates)
    gf = Geofence(
        name=body.name,
        zone_type=body.zone_type,
        polygon=func.ST_GeomFromText(wkt, 4326),
        inmate_id=body.inmate_id,
        case_id=body.case_id,
    )
    db.add(gf)
    db.commit()
    db.refresh(gf)
    log_action(db, user=actor, action="create", entity_type="geofence", entity_id=gf.id, request=request)
    return _to_out(db, gf)


@router.patch("/{geofence_id}", response_model=GeofenceOut)
def update_geofence(
    geofence_id: int,
    body: GeofenceUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_only),
):
    gf = db.get(Geofence, geofence_id)
    if gf is None:
        raise HTTPException(status_code=404, detail="Геозона не найдена")
    data = body.model_dump(exclude_unset=True)
    if "coordinates" in data and data["coordinates"] is not None:
        gf.polygon = func.ST_GeomFromText(coords_to_wkt(data.pop("coordinates")), 4326)
    else:
        data.pop("coordinates", None)
    for k, v in data.items():
        setattr(gf, k, v)
    db.commit()
    db.refresh(gf)
    log_action(db, user=actor, action="update", entity_type="geofence", entity_id=gf.id, request=request)
    return _to_out(db, gf)


@router.delete("/{geofence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_geofence(
    geofence_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_only),
):
    gf = db.get(Geofence, geofence_id)
    if gf is None:
        raise HTTPException(status_code=404, detail="Геозона не найдена")
    db.delete(gf)
    db.commit()
    log_action(db, user=actor, action="delete", entity_type="geofence", entity_id=geofence_id, request=request)
