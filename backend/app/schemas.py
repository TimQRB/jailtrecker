"""Pydantic-схемы REST API."""
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import (
    CaseStatus,
    IncidentType,
    ScheduleRule,
    Severity,
    SupervisionType,
    TamperState,
    UserRole,
    ZoneType,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ------------------------------- auth --------------------------------

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ------------------------------- users -------------------------------

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole = UserRole.admin


class UserCreate(UserBase):
    password: str = Field(min_length=6)


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: UserRole | None = None
    password: str | None = Field(default=None, min_length=6)
    is_active: bool | None = None


class UserOut(ORMModel, UserBase):
    id: int
    is_active: bool
    created_at: datetime


# ------------------------------ inmates ------------------------------

class InmateBase(BaseModel):
    full_name: str
    inmate_number: str
    date_of_birth: date | None = None
    photo_url: str | None = None
    supervisor_id: int | None = None


class InmateCreate(InmateBase):
    pass


class InmateUpdate(BaseModel):
    full_name: str | None = None
    inmate_number: str | None = None
    date_of_birth: date | None = None
    photo_url: str | None = None
    supervisor_id: int | None = None
    is_active: bool | None = None


class InmateOut(ORMModel, InmateBase):
    id: int
    is_active: bool
    created_at: datetime


# ------------------------------- cases -------------------------------

class CaseBase(BaseModel):
    inmate_id: int
    case_number: str
    article: str | None = None
    supervision_type: SupervisionType
    supervising_authority: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = None


class CaseCreate(CaseBase):
    pass


class CaseUpdate(BaseModel):
    case_number: str | None = None
    article: str | None = None
    supervision_type: SupervisionType | None = None
    supervising_authority: str | None = None
    status: CaseStatus | None = None
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = None


class CaseOut(ORMModel, CaseBase):
    id: int
    status: CaseStatus
    created_at: datetime


# ------------------------------ devices ------------------------------

class DeviceBase(BaseModel):
    identifier: str
    imei: str
    dev_type: str = "HC02"
    model_name: str | None = None


class DeviceCreate(DeviceBase):
    inmate_id: int | None = None


class DeviceUpdate(BaseModel):
    identifier: str | None = None
    model_name: str | None = None
    is_active: bool | None = None


class DeviceOut(ORMModel, DeviceBase):
    id: int
    inmate_id: int | None
    api_key: str
    last_seen_at: datetime | None
    last_battery: int | None
    tamper_state: TamperState
    is_active: bool
    created_at: datetime


# ----------------------------- geofences -----------------------------

class GeofenceBase(BaseModel):
    name: str
    zone_type: ZoneType
    # Кольцо координат: список [lon, lat]. Замыкание добавится автоматически.
    coordinates: list[list[float]] = Field(min_length=3)
    inmate_id: int | None = None
    case_id: int | None = None


class GeofenceCreate(GeofenceBase):
    pass


class GeofenceUpdate(BaseModel):
    name: str | None = None
    zone_type: ZoneType | None = None
    coordinates: list[list[float]] | None = None
    is_active: bool | None = None


class GeofenceOut(ORMModel):
    id: int
    name: str
    zone_type: ZoneType
    coordinates: list[list[float]]
    inmate_id: int | None
    case_id: int | None
    is_active: bool
    created_at: datetime


# ----------------------------- schedules -----------------------------

class ScheduleBase(BaseModel):
    inmate_id: int
    geofence_id: int
    rule: ScheduleRule
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    start_time: time
    end_time: time


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleUpdate(BaseModel):
    rule: ScheduleRule | None = None
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    start_time: time | None = None
    end_time: time | None = None
    is_active: bool | None = None


class ScheduleOut(ORMModel, ScheduleBase):
    id: int
    is_active: bool


# ----------------------------- locations -----------------------------

class LocationIngest(BaseModel):
    imei: str
    lat: float
    lon: float
    accuracy: float | None = None
    speed: float | None = None
    battery: int | None = None
    tamper: TamperState | None = None
    recorded_at: datetime | None = None


class LocationOut(ORMModel):
    id: int
    device_id: int
    lat: float
    lon: float
    accuracy: float | None
    speed: float | None
    battery: int | None
    source: str
    recorded_at: datetime


# ----------------------------- incidents -----------------------------

class IncidentOut(ORMModel):
    id: int
    inmate_id: int | None
    device_id: int | None
    incident_type: IncidentType
    severity: Severity
    geofence_id: int | None
    message: str | None
    lat: float | None
    lon: float | None
    acknowledged: bool
    acknowledged_by: int | None
    acknowledged_at: datetime | None
    created_at: datetime


# ------------------------------- audit -------------------------------

class AuditOut(ORMModel):
    id: int
    user_id: int | None
    user_email: str | None
    action: str
    entity_type: str | None
    entity_id: str | None
    detail: str | None
    ip: str | None
    user_agent: str | None
    created_at: datetime
