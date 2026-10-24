"""Worksite ORM model."""

from datetime import datetime
import uuid
from sqlalchemy import Boolean, DateTime, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Worksite(Base):
    """Monitored physical site (e.g. industrial plant, construction yard)."""

    __tablename__ = "worksites"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    location_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    devices: Mapped[list["Device"]] = relationship("Device", back_populates="worksite")  # noqa: F821
    alert_rules: Mapped[list["AlertRule"]] = relationship("AlertRule", back_populates="worksite")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Worksite id={self.id} name={self.name!r} is_active={self.is_active}>"
