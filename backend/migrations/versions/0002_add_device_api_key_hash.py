"""Add api_key_hash column to devices table.

Revision ID: 0002_add_device_api_key_hash
Revises: 0001_initial_schema
Create Date: 2026-10-24 22:05:00.000000

Safe, reversible migration adding per-device SHA-256 API key hash storage
for IoT device ingestion authentication (Module 6).
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0002_add_device_api_key_hash"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add api_key_hash column to devices table."""
    op.add_column(
        "devices",
        sa.Column("api_key_hash", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    """Remove api_key_hash column from devices table."""
    op.drop_column("devices", "api_key_hash")
