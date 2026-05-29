"""CRUD поднадзорных (inmates)."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import log_action
from ..database import get_db
from ..models import Inmate, User, UserRole
from ..schemas import InmateCreate, InmateOut, InmateUpdate
from ..security import require_roles

router = APIRouter(prefix="/api/inmates", tags=["inmates"])
admin_only = require_roles(UserRole.admin)


@router.get("", response_model=list[InmateOut])
def list_inmates(
    active: bool | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    q = select(Inmate).order_by(Inmate.id)
    if active is not None:
        q = q.where(Inmate.is_active.is_(active))
    return db.scalars(q).all()


@router.get("/{inmate_id}", response_model=InmateOut)
def get_inmate(inmate_id: int, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    inmate = db.get(Inmate, inmate_id)
    if inmate is None:
        raise HTTPException(status_code=404, detail="Поднадзорный не найден")
    return inmate


@router.post("", response_model=InmateOut, status_code=status.HTTP_201_CREATED)
def create_inmate(
    body: InmateCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_only),
):
    if db.scalar(select(Inmate).where(Inmate.inmate_number == body.inmate_number)):
        raise HTTPException(status_code=400, detail="Личный номер уже используется")
    inmate = Inmate(**body.model_dump())
    db.add(inmate)
    db.commit()
    db.refresh(inmate)
    log_action(db, user=actor, action="create", entity_type="inmate", entity_id=inmate.id, request=request)
    return inmate


@router.patch("/{inmate_id}", response_model=InmateOut)
def update_inmate(
    inmate_id: int,
    body: InmateUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_only),
):
    inmate = db.get(Inmate, inmate_id)
    if inmate is None:
        raise HTTPException(status_code=404, detail="Поднадзорный не найден")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(inmate, k, v)
    db.commit()
    db.refresh(inmate)
    log_action(db, user=actor, action="update", entity_type="inmate", entity_id=inmate.id, request=request)
    return inmate


@router.delete("/{inmate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inmate(
    inmate_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_only),
):
    inmate = db.get(Inmate, inmate_id)
    if inmate is None:
        raise HTTPException(status_code=404, detail="Поднадзорный не найден")
    db.delete(inmate)
    db.commit()
    log_action(db, user=actor, action="delete", entity_type="inmate", entity_id=inmate_id, request=request)
