"""Просмотр аудит-лога (только admin)."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AuditLog, User, UserRole
from ..schemas import AuditOut
from ..security import require_roles

router = APIRouter(prefix="/api/audit", tags=["audit"])
admin_only = require_roles(UserRole.admin)


@router.get("", response_model=list[AuditOut])
def list_audit(
    user_id: int | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    limit: int = 200,
    offset: int = 0,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    q = select(AuditLog).order_by(AuditLog.created_at.desc())
    if user_id is not None:
        q = q.where(AuditLog.user_id == user_id)
    if action is not None:
        q = q.where(AuditLog.action == action)
    if entity_type is not None:
        q = q.where(AuditLog.entity_type == entity_type)
    return db.scalars(q.offset(offset).limit(min(limit, 1000))).all()
