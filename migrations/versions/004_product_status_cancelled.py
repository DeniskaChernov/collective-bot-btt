"""add product_status cancelled

Revision ID: 004
Revises: 003
Create Date: 2025-03-08

"""

from __future__ import annotations

from alembic import op


revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE product_status ADD VALUE IF NOT EXISTS 'cancelled'")


def downgrade() -> None:
    # В PostgreSQL нельзя удалить значение enum без пересоздания типа — не откатываем.
    pass
