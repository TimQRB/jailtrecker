"""Сидирование демо-админа. Схему БД накатывает Alembic (см. backend/alembic).

В отличие от SafeMektep здесь НЕТ create_all — миграции обязательны (known issue #4).
"""
import logging

from sqlalchemy import select

from .database import SessionLocal
from .config import settings
from .models import User, UserRole
from .security import hash_password

logger = logging.getLogger("jailtracker.init")


def seed_admin() -> None:
    db = SessionLocal()
    try:
        existing = db.scalar(select(User).where(User.email == settings.admin_email))
        if existing:
            return
        admin = User(
            email=settings.admin_email,
            full_name=settings.admin_full_name,
            role=UserRole.admin,
            password_hash=hash_password(settings.admin_password),
        )
        db.add(admin)
        db.commit()
        logger.info("Сидирован администратор: %s", settings.admin_email)
    finally:
        db.close()
