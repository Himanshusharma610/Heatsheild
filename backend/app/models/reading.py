"""Sensor reading ORM model."""

from datetime import datetime
from decimal import Decimal
import uuid
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SensorReading(Base):
    """Time-series environmental measurement emitted by an ESP32 device."""

    __tablename__ = "sensor_readings"
    __table_args__ = (
        UniqueConstraint("device_id", "event_id", name="uq_readings_device_event"),
        CheckConstraint(
            "relative_humidity_pct IS NULL OR (relative_humidity_pct >= 0 AND relative_humidity_pct <= 100)",
            name="ck_readings_humidity_range",
        ),
        CheckConstraint(
            "quality_status IN ('valid', 'suspect', 'invalid', 'missing')",
            name="ck_readings_quality_status",
        ),
        CheckConstraint(
            "source_mode IN ('hardware', 'simulated')",
            name="ck_readings_source_mode",
        ),
        Index("ix_readings_device_received", "device_id", text("received_at DESC")),
        Index("ix_readings_device_measured", "device_id", text("measured_at DESC")),
        Index("ix_readings_quality", "quality_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("devices.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    event_id: Mapped[str] = mapped_column(String(100), nullable=False)
    measured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    temperature_c: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    relative_humidity_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    quality_status: Mapped[str] = mapped_column(String(20), default="valid", nullable=False)
    source_mode: Mapped[str] = mapped_column(String(20), default="hardware", nullable=False)
    firmware_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="sensor_readings")  # noqa: F821
    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="reading")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<SensorReading id={self.id} device_id={self.device_id} "
            f"event_id={self.event_id!r} temp={self.temperature_c} humidity={self.relative_humidity_pct} "
            f"quality={self.quality_status!r} source={self.source_mode!r}>"
        )
