"""CRUD браслетов, привязка к поднадзорному, команда locate-now."""
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import log_action
from ..database import get_db
from ..device_commands import send_command
from ..models import Device, Inmate, User, UserRole
from ..schemas import DeviceCreate, DeviceOut, DeviceUpdate
from ..security import require_roles

router = APIRouter(prefix="/api/devices", tags=["devices"])
admin_only = require_roles(UserRole.admin)


@router.get("", response_model=list[DeviceOut])
def list_devices(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    return db.scalars(select(Device).order_by(Device.id)).all()


@router.post("", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
def create_device(
    body: DeviceCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_only),
):
    if db.scalar(select(Device).where(Device.imei == body.imei)):
        raise HTTPException(status_code=400, detail="Устройство с таким IMEI уже есть")
    device = Device(**body.model_dump(), api_key=secrets.token_hex(24))
    db.add(device)
    db.commit()
    db.refresh(device)
    log_action(db, user=actor, action="create", entity_type="device", entity_id=device.id, request=request)
    return device


@router.patch("/{device_id}", response_model=DeviceOut)
def update_device(
    device_id: int,
    body: DeviceUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_only),
):
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Устройство не найдено")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(device, k, v)
    db.commit()
    db.refresh(device)
    log_action(db, user=actor, action="update", entity_type="device", entity_id=device.id, request=request)
    return device


@router.post("/{device_id}/assign/{inmate_id}", response_model=DeviceOut)
def assign_device(
    device_id: int,
    inmate_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_only),
):
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Устройство не найдено")
    if db.get(Inmate, inmate_id) is None:
        raise HTTPException(status_code=404, detail="Поднадзорный не найден")
    device.inmate_id = inmate_id
    db.commit()
    db.refresh(device)
    log_action(
        db, user=actor, action="assign", entity_type="device", entity_id=device.id,
        detail=f"inmate={inmate_id}", request=request,
    )
    return device


@router.post("/{device_id}/locate-now", status_code=status.HTTP_202_ACCEPTED)
async def locate_now(
    device_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_only),
):
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Устройство не найдено")
    await send_command(device.imei, "locate_now")
    log_action(db, user=actor, action="locate_now", entity_type="device", entity_id=device.id, request=request)
    return {"status": "queued"}


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(
    device_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_only),
):
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Устройство не найдено")
    db.delete(device)
    db.commit()
    log_action(db, user=actor, action="delete", entity_type="device", entity_id=device_id, request=request)
