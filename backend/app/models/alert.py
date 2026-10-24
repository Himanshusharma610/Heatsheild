"""Alert-related ORM models: AlertRule, Alert, and AlertAcknowledgement."""

from datetime import datetime
from decimal import Decimal
from typing import Any
import uuid
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base

# Dialect-agnostic JSONB: uses PostgreSQL native JSONB in Postgres, falls back to JSON in SQLite
JSONB_TYPE = JSONB().with_variant(JSON(), "sqlite")


class AlertRule(Base):
    """Configurable alert rule evaluated against incoming measurements."""

    __tablename__ = "alert_rules"
    __table_args__ = (
        CheckConstraint(
            "operator IN ('gt', 'gte', 'lt', 'lte', 'eq')",
            name="ck_alert_rules_operator",
        ),
        CheckConstraint(
            "severity IN ('info', 'warning', 'critical', 'emergency')",
            name="ck_alert_rules_severity",
        ),
        Index("ix_alert_rules_worksite", "worksite_id"),
        Index("ix_alert_rules_enabled", "is_enabled"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    worksite_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("worksites.id", ondelete="SET NULL"),
        nullable=True,
    )
    metric: Mapped[str] = mapped_column(String(50), nullable=False)
    operator: Mapped[str] = mapped_column(String(10), nullable=False)
    threshold_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    threshold_params: Mapped[dict[str, Any] | None] = mapped_column(JSONB_TYPE, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rule_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __init__(self, **kwargs: Any) -> None:
        if "rule_version" not in kwargs:
            kwargs["rule_version"] = 1
        if "is_enabled" not in kwargs:
            kwargs["is_enabled"] = True
        super().__init__(**kwargs)

    # Relationships
    worksite: Mapped["Worksite | None"] = relationship("Worksite", back_populates="alert_rules")  # noqa: F821
    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="alert_rule")

    def __repr__(self) -> str:
        return f"<AlertRule id={self.id} name={self.name!r} metric={self.metric!r} severity={self.severity!r}>"


class Alert(Base):
    """Alert event triggered by a reading, device event, or manual trigger."""

    __tablename__ = "alerts"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('info', 'warning', 'critical', 'emergency')",
            name="ck_alerts_severity",
        ),
        CheckConstraint(
            "status IN ('triggered', 'acknowledged', 'resolved', 'expired')",
            name="ck_alerts_status",
        ),
        Index("ix_alerts_device_status", "device_id", "status"),
        Index("ix_alerts_triggered", text("triggered_at DESC")),
        Index("ix_alerts_dedup", "deduplication_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("devices.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    reading_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sensor_readings.id", ondelete="SET NULL"),
        nullable=True,
    )
    alert_rule_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("alert_rules.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="triggered", nullable=False, index=True)
    rule_version_snapshot: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deduplication_key: Mapped[str | None] = mapped_column(String(200), nullable=True)
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="alerts")  # noqa: F821
    reading: Mapped["SensorReading | None"] = relationship("SensorReading", back_populates="alerts")  # noqa: F821
    alert_rule: Mapped["AlertRule | None"] = relationship("AlertRule", back_populates="alerts")
    acknowledgements: Mapped[list["AlertAcknowledgement"]] = relationship(
        "AlertAcknowledgement",
        back_populates="alert",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Alert id={self.id} device_id={self.device_id} event_type={self.event_type!r} "
            f"severity={self.severity!r} status={self.status!r}>"
        )


class AlertAcknowledgement(Base):
    """Documented safety action or acknowledgement response taken for an active alert."""

    __tablename__ = "alert_acknowledgements"
    __table_args__ = (
        Index("ix_ack_alert", "alert_id"),
        Index("ix_ack_actor", "actor_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("alerts.id", ondelete="CASCADE"),
        nullable=False,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action_taken: Mapped[str | None] = mapped_column(Text, nullable=True)
    acknowledged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    alert: Mapped["Alert"] = relationship("Alert", back_populates="acknowledgements")
    actor: Mapped["User | None"] = relationship("User", back_populates="acknowledgements")  # noqa: F821

    def __repr__(self) -> str:
        return f"<AlertAcknowledgement id={self.id} alert_id={self.alert_id} actor_id={self.actor_id}>"
