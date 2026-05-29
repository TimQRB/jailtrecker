"""Запись в аудит-лог. Закрывает known issue SafeMektep #9 (нет аудита доступа)."""
from fastapi import Request
from sqlalchemy.orm import Session

from .models import AuditLog, User


def log_action(
    db: Session,
    *,
    user: User | None = None,
    action: str,
    entity_type: str | None = None,
    entity_id: str | int | None = None,
    detail: str | None = None,
    request: Request | None = None,
    commit: bool = True,
) -> AuditLog:
    entry = AuditLog(
        user_id=user.id if user else None,
        user_email=user.email if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        detail=detail,
        ip=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.add(entry)
    if commit:
        db.commit()
    return entry
