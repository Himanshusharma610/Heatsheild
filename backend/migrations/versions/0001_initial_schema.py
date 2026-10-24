"""Initial database schema for HeatShield Bharat.

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-10-24 16:00:00.000000

Creates the 8 foundational entities defined in Module 2:
- worksites
- devices
- sensor_readings
- alert_rules
- alerts
- alert_acknowledgements
- users
- audit_logs
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Worksites
    op.create_table(
        "worksites",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("location_description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. Users
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), server_default="viewer", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role IN ('viewer', 'supervisor', 'admin')", name="ck_users_role"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_role", "users", ["role"])

    # 3. Devices
    op.create_table(
        "devices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("device_code", sa.String(length=100), nullable=False),
        sa.Column("worksite_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="registered", nullable=False),
        sa.Column("firmware_version", sa.String(length=50), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('registered', 'online', 'offline', 'deactivated')",
            name="ck_devices_status",
        ),
        sa.ForeignKeyConstraint(["worksite_id"], ["worksites.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_code", name="uq_devices_device_code"),
    )
    op.create_index("ix_devices_worksite_id", "devices", ["worksite_id"])
    op.create_index("ix_devices_status", "devices", ["status"])

    # 4. Sensor Readings
    jsonb_type = postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")

    op.create_table(
        "sensor_readings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.String(length=100), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("temperature_c", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("relative_humidity_pct", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("quality_status", sa.String(length=20), server_default="valid", nullable=False),
        sa.Column("source_mode", sa.String(length=20), server_default="hardware", nullable=False),
        sa.Column("firmware_version", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "relative_humidity_pct IS NULL OR (relative_humidity_pct >= 0 AND relative_humidity_pct <= 100)",
            name="ck_readings_humidity_range",
        ),
        sa.CheckConstraint(
            "quality_status IN ('valid', 'suspect', 'invalid', 'missing')",
            name="ck_readings_quality_status",
        ),
        sa.CheckConstraint(
            "source_mode IN ('hardware', 'simulated')",
            name="ck_readings_source_mode",
        ),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_id", "event_id", name="uq_readings_device_event"),
    )
    op.create_index("ix_readings_device_received", "sensor_readings", ["device_id", sa.text("received_at DESC")])
    op.create_index("ix_readings_device_measured", "sensor_readings", ["device_id", sa.text("measured_at DESC")])
    op.create_index("ix_readings_quality", "sensor_readings", ["quality_status"])

    # 5. Alert Rules
    op.create_table(
        "alert_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("worksite_id", sa.Uuid(), nullable=True),
        sa.Column("metric", sa.String(length=50), nullable=False),
        sa.Column("operator", sa.String(length=10), nullable=False),
        sa.Column("threshold_value", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("threshold_params", jsonb_type, nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("rule_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "operator IN ('gt', 'gte', 'lt', 'lte', 'eq')",
            name="ck_alert_rules_operator",
        ),
        sa.CheckConstraint(
            "severity IN ('info', 'warning', 'critical', 'emergency')",
            name="ck_alert_rules_severity",
        ),
        sa.ForeignKeyConstraint(["worksite_id"], ["worksites.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_rules_worksite", "alert_rules", ["worksite_id"])
    op.create_index("ix_alert_rules_enabled", "alert_rules", ["is_enabled"])

    # 6. Alerts
    op.create_table(
        "alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("reading_id", sa.Uuid(), nullable=True),
        sa.Column("alert_rule_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="triggered", nullable=False),
        sa.Column("rule_version_snapshot", sa.Integer(), nullable=True),
        sa.Column("deduplication_key", sa.String(length=200), nullable=True),
        sa.Column("triggered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "severity IN ('info', 'warning', 'critical', 'emergency')",
            name="ck_alerts_severity",
        ),
        sa.CheckConstraint(
            "status IN ('triggered', 'acknowledged', 'resolved', 'expired')",
            name="ck_alerts_status",
        ),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reading_id"], ["sensor_readings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["alert_rule_id"], ["alert_rules.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alerts_device_status", "alerts", ["device_id", "status"])
    op.create_index("ix_alerts_triggered", "alerts", [sa.text("triggered_at DESC")])
    op.create_index("ix_alerts_dedup", "alerts", ["deduplication_key"])

    # 7. Alert Acknowledgements
    op.create_table(
        "alert_acknowledgements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("alert_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("action_taken", sa.Text(), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ack_alert", "alert_acknowledgements", ["alert_id"])
    op.create_index("ix_ack_actor", "alert_acknowledgements", ["actor_id"])

    # 8. Audit Logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("target_entity_type", sa.String(length=50), nullable=True),
        sa.Column("target_entity_id", sa.Uuid(), nullable=True),
        sa.Column("metadata", jsonb_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_actor", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_action", "audit_logs", ["action_type"])
    op.create_index("ix_audit_target", "audit_logs", ["target_entity_type", "target_entity_id"])
    op.create_index("ix_audit_created", "audit_logs", [sa.text("created_at DESC")])


def downgrade() -> None:
    # Reverse order for safe FK drop
    op.drop_table("audit_logs")
    op.drop_table("alert_acknowledgements")
    op.drop_table("alerts")
    op.drop_table("alert_rules")
    op.drop_table("sensor_readings")
    op.drop_table("devices")
    op.drop_table("users")
    op.drop_table("worksites")
