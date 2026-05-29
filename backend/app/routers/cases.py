"""CRUD дел (cases)."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import log_action
from ..database import get_db
from ..models import Case, Inmate, User, UserRole
from ..schemas import CaseCreate, CaseOut, CaseUpdate
from ..security import require_roles

router = APIRouter(prefix="/api/cases", tags=["cases"])
admin_only = require_roles(UserRole.admin)


@router.get("", response_model=list[CaseOut])
def list_cases(
    inmate_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    q = select(Case).order_by(Case.id)
    if inmate_id is not None:
        q = q.where(Case.inmate_id == inmate_id)
    return db.scalars(q).all()


@router.post("", response_model=CaseOut, status_code=status.HTTP_201_CREATED)
def create_case(
    body: CaseCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_only),
):
    if db.get(Inmate, body.inmate_id) is None:
        raise HTTPException(status_code=404, detail="Поднадзорный не найден")
    if db.scalar(select(Case).where(Case.case_number == body.case_number)):
        raise HTTPException(status_code=400, detail="Номер дела уже используется")
    case = Case(**body.model_dump())
    db.add(case)
    db.commit()
    db.refresh(case)
    log_action(db, user=actor, action="create", entity_type="case", entity_id=case.id, request=request)
    return case


@router.patch("/{case_id}", response_model=CaseOut)
def update_case(
    case_id: int,
    body: CaseUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_only),
):
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Дело не найдено")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(case, k, v)
    db.commit()
    db.refresh(case)
    log_action(db, user=actor, action="update", entity_type="case", entity_id=case.id, request=request)
    return case


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case(
    case_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_only),
):
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Дело не найдено")
    db.delete(case)
    db.commit()
    log_action(db, user=actor, action="delete", entity_type="case", entity_id=case_id, request=request)
