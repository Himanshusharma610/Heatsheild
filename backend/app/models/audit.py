"""Audit log ORM model."""

from datetime import datetime
from typing import Any
import uuid
from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base

JSONB_TYPE = JSONB().with_variant(JSON(), "sqlite")


class AuditLog(Base):
    """Append-only audit log for administrative, device, and security actions."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_actor", "actor_id"),
        Index("ix_audit_action", "action_type"),
        Index("ix_audit_target", "target_entity_type", "target_entity_id"),
        Index("ix_audit_created", text("created_at DESC")),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    # Use mapped_column("metadata", ...) so DB column is 'metadata' while avoiding conflict with Base.metadata
    extra_data: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB_TYPE, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    actor: Mapped["User | None"] = relationship("User", back_populates="audit_logs")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} action={self.action_type!r} "
            f"target={self.target_entity_type}:{self.target_entity_id} actor_id={self.actor_id}>"
        )
