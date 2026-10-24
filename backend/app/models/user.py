"""User account ORM model."""

from datetime import datetime
import uuid
from sqlalchemy import Boolean, CheckConstraint, DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    """Supervisor or dashboard administrator account."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('viewer', 'supervisor', 'admin')",
            name="ck_users_role",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="viewer", nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    acknowledgements: Mapped[list["AlertAcknowledgement"]] = relationship(  # noqa: F821
        "AlertAcknowledgement",
        back_populates="actor",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="actor")  # noqa: F821

    def __repr__(self) -> str:
        # Crucial security rule: never print password_hash in representations or logs
        return f"<User id={self.id} email={self.email!r} role={self.role!r} is_active={self.is_active}>"
