"""CRUD расписаний/комендантского часа."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import log_action
from ..database import get_db
from ..models import Geofence, Inmate, Schedule, User, UserRole
from ..schemas import ScheduleCreate, ScheduleOut, ScheduleUpdate
from ..security import require_roles

router = APIRouter(prefix="/api/schedules", tags=["schedules"])
admin_only = require_roles(UserRole.admin)


@router.get("", response_model=list[ScheduleOut])
def list_schedules(
    inmate_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    q = select(Schedule).order_by(Schedule.id)
    if inmate_id is not None:
        q = q.where(Schedule.inmate_id == inmate_id)
    return db.scalars(q).all()


@router.post("", response_model=ScheduleOut, status_code=status.HTTP_201_CREATED)
def create_schedule(
    body: ScheduleCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_only),
):
    if db.get(Inmate, body.inmate_id) is None:
        raise HTTPException(status_code=404, detail="Поднадзорный не найден")
    if db.get(Geofence, body.geofence_id) is None:
        raise HTTPException(status_code=404, detail="Геозона не найдена")
    sch = Schedule(**body.model_dump())
    db.add(sch)
    db.commit()
    db.refresh(sch)
    log_action(db, user=actor, action="create", entity_type="schedule", entity_id=sch.id, request=request)
    return sch


@router.patch("/{schedule_id}", response_model=ScheduleOut)
def update_schedule(
    schedule_id: int,
    body: ScheduleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_only),
):
    sch = db.get(Schedule, schedule_id)
    if sch is None:
        raise HTTPException(status_code=404, detail="Расписание не найдено")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(sch, k, v)
    db.commit()
    db.refresh(sch)
    log_action(db, user=actor, action="update", entity_type="schedule", entity_id=sch.id, request=request)
    return sch


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
    schedule_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_only),
):
    sch = db.get(Schedule, schedule_id)
    if sch is None:
        raise HTTPException(status_code=404, detail="Расписание не найдено")
    db.delete(sch)
    db.commit()
    log_action(db, user=actor, action="delete", entity_type="schedule", entity_id=schedule_id, request=request)
