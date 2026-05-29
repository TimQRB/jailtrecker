"""ORM-модели jailtracker.

Сущности спроектированы под все три сценария надзора одновременно:
  - домашний арест (геозоны дом/работа + комендантский час через schedules),
  - внутри ИУ (зоны корпусов + запретные зоны),
  - конвоирование (маршрутный коридор как геозона типа route_corridor).

Конкретика сценария задаётся на уровне дела (case.supervision_type) и типов геозон.
"""
import enum
from datetime import datetime, date, time

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


# ----------------------------- перечисления -----------------------------

class UserRole(str, enum.Enum):
    admin = "admin"            # администрация ИУ — полный доступ (пока единственная роль)
    warden = "warden"          # надзиратель / оперативный дежурный (задел на будущее)
    inspector = "inspector"    # инспектор УИИ (задел на будущее)


class SupervisionType(str, enum.Enum):
    house_arrest = "house_arrest"   # домашний арест
    facility = "facility"           # внутри ИУ
    convoy = "convoy"               # конвоирование


class CaseStatus(str, enum.Enum):
    active = "active"
    suspended = "suspended"
    closed = "closed"


class ZoneType(str, enum.Enum):
    home = "home"                   # дом (должен находиться внутри)
    work = "work"                   # разрешённое место работы/учёбы
    allowed = "allowed"             # иная разрешённая зона
    forbidden = "forbidden"         # запретная зона (алерт при входе)
    perimeter = "perimeter"         # периметр ИУ (алерт при выходе)
    route_corridor = "route_corridor"  # коридор маршрута конвоя (алерт при выходе)


class ScheduleRule(str, enum.Enum):
    must_be_inside = "must_be_inside"   # в эти часы обязан быть внутри geofence (комендантский)
    allowed_outside = "allowed_outside"  # в эти часы разрешён выход из geofence


class IncidentType(str, enum.Enum):
    exit_zone = "exit_zone"                 # выход из обязательной зоны
    enter_forbidden = "enter_forbidden"     # вход в запретную зону
    curfew_violation = "curfew_violation"   # нарушение комендантского часа
    route_deviation = "route_deviation"     # отклонение от маршрута
    tamper = "tamper"                       # вскрытие/срез ремня браслета
    low_battery = "low_battery"
    device_offline = "device_offline"
    sos = "sos"


class Severity(str, enum.Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class TamperState(str, enum.Enum):
    ok = "ok"
    opened = "opened"       # корпус вскрыт
    strap_cut = "strap_cut"  # ремень срезан


# ------------------------------- таблицы --------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, native_enum=False), default=UserRole.admin)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Inmate(Base):
    __tablename__ = "inmates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    inmate_number: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # инспектор/надзиратель, ответственный за поднадзорного (задел на будущие роли)
    supervisor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    cases: Mapped[list["Case"]] = relationship(back_populates="inmate", cascade="all, delete-orphan")
    device: Mapped["Device | None"] = relationship(back_populates="inmate", uselist=False)


class Case(Base):
    """Дело: правовое основание надзора и его тип."""
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    inmate_id: Mapped[int] = mapped_column(ForeignKey("inmates.id"), nullable=False, index=True)
    case_number: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    article: Mapped[str | None] = mapped_column(String(255), nullable=True)  # статья
    supervision_type: Mapped[SupervisionType] = mapped_column(
        Enum(SupervisionType, native_enum=False), nullable=False
    )
    supervising_authority: Mapped[str | None] = mapped_column(String(255), nullable=True)  # УИИ/ИУ
    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus, native_enum=False), default=CaseStatus.active
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    inmate: Mapped["Inmate"] = relationship(back_populates="cases")


class Device(Base):
    """Электронный браслет."""
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    identifier: Mapped[str] = mapped_column(String(64), nullable=False)
    imei: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    dev_type: Mapped[str] = mapped_column(String(32), default="HC02")
    model_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    inmate_id: Mapped[int | None] = mapped_column(ForeignKey("inmates.id"), nullable=True)
    api_key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_battery: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tamper_state: Mapped[TamperState] = mapped_column(
        Enum(TamperState, native_enum=False), default=TamperState.ok
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    inmate: Mapped["Inmate | None"] = relationship(back_populates="device")


class Geofence(Base):
    __tablename__ = "geofences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    zone_type: Mapped[ZoneType] = mapped_column(Enum(ZoneType, native_enum=False), nullable=False)
    # POLYGON в WGS84. Для маршрута конвоя — забуференный коридор как полигон.
    polygon: Mapped[str] = mapped_column(Geometry("POLYGON", srid=4326), nullable=False)
    # Привязка к конкретному поднадзорному (NULL = общая зона, напр. периметр ИУ).
    inmate_id: Mapped[int | None] = mapped_column(ForeignKey("inmates.id"), nullable=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Schedule(Base):
    """Расписание/комендантский час, привязанное к зоне."""
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    inmate_id: Mapped[int] = mapped_column(ForeignKey("inmates.id"), nullable=False, index=True)
    geofence_id: Mapped[int] = mapped_column(ForeignKey("geofences.id"), nullable=False)
    rule: Mapped[ScheduleRule] = mapped_column(Enum(ScheduleRule, native_enum=False), nullable=False)
    # 0=Пн ... 6=Вс; NULL = ежедневно
    day_of_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class LocationPoint(Base):
    __tablename__ = "location_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False, index=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    battery: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="gps")  # gps/http/tcp
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class DeviceZoneState(Base):
    """Текущее состояние внутри/снаружи для пары устройство×геозона."""
    __tablename__ = "device_zone_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False, index=True)
    geofence_id: Mapped[int] = mapped_column(ForeignKey("geofences.id"), nullable=False, index=True)
    is_inside: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Incident(Base):
    """Инцидент (бывш. event): нарушение, тревога, технический алерт."""
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    inmate_id: Mapped[int | None] = mapped_column(ForeignKey("inmates.id"), nullable=True, index=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"), nullable=True)
    incident_type: Mapped[IncidentType] = mapped_column(
        Enum(IncidentType, native_enum=False), nullable=False
    )
    severity: Mapped[Severity] = mapped_column(Enum(Severity, native_enum=False), default=Severity.warning)
    geofence_id: Mapped[int | None] = mapped_column(ForeignKey("geofences.id"), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class AuditLog(Base):
    """Аудит доступа и действий — обязателен для пенитенциарной системы."""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    user_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)   # login, create, update, delete, view, ack...
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
