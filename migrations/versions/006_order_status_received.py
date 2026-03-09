"""add order_status received

Revision ID: 006
Revises: 005
Create Date: 2026-03-09

"""

from __future__ import annotations

from alembic import op


revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'received'")


def downgrade() -> None:
    # PostgreSQL enum values are not removed in downgrade without recreating the type.
    pass
