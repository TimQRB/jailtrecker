"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-29
"""
from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="admin"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "inmates",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("inmate_number", sa.String(64), nullable=False, unique=True),
        sa.Column("date_of_birth", sa.Date, nullable=True),
        sa.Column("photo_url", sa.String(512), nullable=True),
        sa.Column("supervisor_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_inmates_inmate_number", "inmates", ["inmate_number"])

    op.create_table(
        "cases",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("inmate_id", sa.Integer, sa.ForeignKey("inmates.id"), nullable=False),
        sa.Column("case_number", sa.String(64), nullable=False, unique=True),
        sa.Column("article", sa.String(255), nullable=True),
        sa.Column("supervision_type", sa.String(32), nullable=False),
        sa.Column("supervising_authority", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("start_date", sa.Date, nullable=True),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_cases_inmate_id", "cases", ["inmate_id"])
    op.create_index("ix_cases_case_number", "cases", ["case_number"])

    op.create_table(
        "devices",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("identifier", sa.String(64), nullable=False),
        sa.Column("imei", sa.String(32), nullable=False, unique=True),
        sa.Column("dev_type", sa.String(32), nullable=False, server_default="HC02"),
        sa.Column("model_name", sa.String(64), nullable=True),
        sa.Column("inmate_id", sa.Integer, sa.ForeignKey("inmates.id"), nullable=True),
        sa.Column("api_key", sa.String(128), nullable=False, unique=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_battery", sa.Integer, nullable=True),
        sa.Column("tamper_state", sa.String(32), nullable=False, server_default="ok"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_devices_imei", "devices", ["imei"])
    op.create_index("ix_devices_api_key", "devices", ["api_key"])

    op.create_table(
        "geofences",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("zone_type", sa.String(32), nullable=False),
        sa.Column(
            "polygon",
            geoalchemy2.types.Geometry(geometry_type="POLYGON", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("inmate_id", sa.Integer, sa.ForeignKey("inmates.id"), nullable=True),
        sa.Column("case_id", sa.Integer, sa.ForeignKey("cases.id"), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute("CREATE INDEX ix_geofences_polygon ON geofences USING GIST (polygon)")

    op.create_table(
        "schedules",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("inmate_id", sa.Integer, sa.ForeignKey("inmates.id"), nullable=False),
        sa.Column("geofence_id", sa.Integer, sa.ForeignKey("geofences.id"), nullable=False),
        sa.Column("rule", sa.String(32), nullable=False),
        sa.Column("day_of_week", sa.Integer, nullable=True),
        sa.Column("start_time", sa.Time, nullable=False),
        sa.Column("end_time", sa.Time, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_schedules_inmate_id", "schedules", ["inmate_id"])

    op.create_table(
        "location_points",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("device_id", sa.Integer, sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("lat", sa.Float, nullable=False),
        sa.Column("lon", sa.Float, nullable=False),
        sa.Column("accuracy", sa.Float, nullable=True),
        sa.Column("speed", sa.Float, nullable=True),
        sa.Column("battery", sa.Integer, nullable=True),
        sa.Column("source", sa.String(16), nullable=False, server_default="gps"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_location_points_device_id", "location_points", ["device_id"])
    op.create_index("ix_location_points_recorded_at", "location_points", ["recorded_at"])

    op.create_table(
        "device_zone_states",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("device_id", sa.Integer, sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("geofence_id", sa.Integer, sa.ForeignKey("geofences.id"), nullable=False),
        sa.Column("is_inside", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_dzs_device_id", "device_zone_states", ["device_id"])
    op.create_index("ix_dzs_geofence_id", "device_zone_states", ["geofence_id"])

    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("inmate_id", sa.Integer, sa.ForeignKey("inmates.id"), nullable=True),
        sa.Column("device_id", sa.Integer, sa.ForeignKey("devices.id"), nullable=True),
        sa.Column("incident_type", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False, server_default="warning"),
        sa.Column("geofence_id", sa.Integer, sa.ForeignKey("geofences.id"), nullable=True),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("lat", sa.Float, nullable=True),
        sa.Column("lon", sa.Float, nullable=True),
        sa.Column("acknowledged", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("acknowledged_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_incidents_inmate_id", "incidents", ["inmate_id"])
    op.create_index("ix_incidents_created_at", "incidents", ["created_at"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("user_email", sa.String(255), nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=True),
        sa.Column("entity_id", sa.String(64), nullable=True),
        sa.Column("detail", sa.Text, nullable=True),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("incidents")
    op.drop_table("device_zone_states")
    op.drop_table("location_points")
    op.drop_table("schedules")
    op.execute("DROP INDEX IF EXISTS ix_geofences_polygon")
    op.drop_table("geofences")
    op.drop_table("devices")
    op.drop_table("cases")
    op.drop_table("inmates")
    op.drop_table("users")
