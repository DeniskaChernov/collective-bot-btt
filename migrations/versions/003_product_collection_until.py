"""add product collection_until (3-day window)

Revision ID: 003
Revises: 002
Create Date: 2025-03-08

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("collection_until", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_products_collection_until", "products", ["collection_until"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_products_collection_until", "products")
    op.drop_column("products", "collection_until")
