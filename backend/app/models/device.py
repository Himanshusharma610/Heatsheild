"""Device ORM model."""

from datetime import datetime
import uuid
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Device(Base):
    """Registered physical sensor node in the field."""

    __tablename__ = "devices"
    __table_args__ = (
        CheckConstraint(
            "status IN ('registered', 'online', 'offline', 'deactivated')",
            name="ck_devices_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    worksite_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("worksites.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="registered", nullable=False, index=True)
    firmware_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    worksite: Mapped["Worksite"] = relationship("Worksite", back_populates="devices")  # noqa: F821
    sensor_readings: Mapped[list["SensorReading"]] = relationship("SensorReading", back_populates="device")  # noqa: F821
    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="device")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Device id={self.id} code={self.device_code!r} status={self.status!r}>"
