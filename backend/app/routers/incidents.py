"""Лента инцидентов + квитирование (ack)."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import log_action
from ..database import get_db
from ..models import Incident, Severity, User, UserRole
from ..schemas import IncidentOut
from ..security import require_roles

router = APIRouter(prefix="/api/incidents", tags=["incidents"])
admin_only = require_roles(UserRole.admin)


@router.get("", response_model=list[IncidentOut])
def list_incidents(
    inmate_id: int | None = None,
    severity: Severity | None = None,
    acknowledged: bool | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    q = select(Incident).order_by(Incident.created_at.desc())
    if inmate_id is not None:
        q = q.where(Incident.inmate_id == inmate_id)
    if severity is not None:
        q = q.where(Incident.severity == severity)
    if acknowledged is not None:
        q = q.where(Incident.acknowledged.is_(acknowledged))
    return db.scalars(q.limit(min(limit, 500))).all()


@router.post("/{incident_id}/ack", response_model=IncidentOut)
def ack_incident(
    incident_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_only),
):
    inc = db.get(Incident, incident_id)
    if inc is None:
        raise HTTPException(status_code=404, detail="Инцидент не найден")
    inc.acknowledged = True
    inc.acknowledged_by = actor.id
    inc.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(inc)
    log_action(db, user=actor, action="ack", entity_type="incident", entity_id=inc.id, request=request)
    return inc
