"""add user language

Revision ID: 005
Revises: 004
Create Date: 2026-03-09

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("language", sa.String(length=2), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "language")
