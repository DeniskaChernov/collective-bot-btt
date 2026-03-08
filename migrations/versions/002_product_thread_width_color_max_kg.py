"""add product thread_width color max_weight_per_order

Revision ID: 002
Revises: 001
Create Date: 2025-03-08

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("thread_width", sa.String(255), nullable=True))
    op.add_column("products", sa.Column("color", sa.String(128), nullable=True))
    op.add_column("products", sa.Column("max_weight_per_order", sa.Integer(), nullable=False, server_default="25"))
    op.create_check_constraint("ck_products_max_weight_per_order_min", "products", "max_weight_per_order >= 5")
    op.create_check_constraint("ck_products_max_weight_per_order_max", "products", "max_weight_per_order <= 500")


def downgrade() -> None:
    op.drop_constraint("ck_products_max_weight_per_order_max", "products", type_="check")
    op.drop_constraint("ck_products_max_weight_per_order_min", "products", type_="check")
    op.drop_column("products", "max_weight_per_order")
    op.drop_column("products", "color")
    op.drop_column("products", "thread_width")
