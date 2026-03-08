"""init

Revision ID: 001
Revises:
Create Date: 2025-03-08

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(64), nullable=True),
        sa.Column("first_name", sa.String(128), nullable=True),
        sa.Column("last_name", sa.String(128), nullable=True),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=False)
    op.create_index("ix_users_phone", "users", ["phone"], unique=False)

    op.create_table(
        "products",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("article", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("profile", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("min_weight", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("total_weight", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.Enum("open", "waiting_24h", "closed", name="product_status"), nullable=False, server_default="open"),
        sa.Column("threshold_reached_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("article", name="uq_products_article"),
        sa.CheckConstraint("min_weight > 0", name="ck_products_min_weight_positive"),
        sa.CheckConstraint("total_weight >= 0", name="ck_products_total_weight_nonneg"),
    )
    op.create_index("ix_products_status", "products", ["status"], unique=False)
    op.create_index("ix_products_threshold_reached_at", "products", ["threshold_reached_at"], unique=False)

    op.create_table(
        "cart_items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "product_id", name="uq_cart_user_product"),
        sa.CheckConstraint("weight >= 0", name="ck_cart_weight_nonneg"),
        sa.CheckConstraint("(weight % 5) = 0", name="ck_cart_weight_multiple_of_5"),
    )
    op.create_index("ix_cart_user_id", "cart_items", ["user_id"], unique=False)
    op.create_index("ix_cart_product_id", "cart_items", ["product_id"], unique=False)

    op.create_table(
        "orders",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("weight_total", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("pending", "confirmed", "cancelled", "completed", name="order_status"), nullable=False, server_default="pending"),
        sa.Column("fulfillment_type", sa.Enum("pickup", "delivery", "uzum_market", name="fulfillment_type"), nullable=False),
        sa.Column("delivery_address", sa.Text(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("weight_total > 0", name="ck_orders_weight_positive"),
    )
    op.create_index("ix_orders_created_at", "orders", ["created_at"], unique=False)
    op.create_index("ix_orders_fulfillment_type", "orders", ["fulfillment_type"], unique=False)
    op.create_index("ix_orders_status", "orders", ["status"], unique=False)
    op.create_index("ix_orders_user_id", "orders", ["user_id"], unique=False)
    op.create_index("ix_orders_product_id", "orders", ["product_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_orders_product_id", "orders")
    op.drop_index("ix_orders_user_id", "orders")
    op.drop_index("ix_orders_status", "orders")
    op.drop_index("ix_orders_fulfillment_type", "orders")
    op.drop_index("ix_orders_created_at", "orders")
    op.drop_table("orders")

    op.drop_index("ix_cart_product_id", "cart_items")
    op.drop_index("ix_cart_user_id", "cart_items")
    op.drop_table("cart_items")

    op.drop_index("ix_products_threshold_reached_at", "products")
    op.drop_index("ix_products_status", "products")
    op.drop_table("products")

    op.drop_index("ix_users_phone", "users")
    op.drop_index("ix_users_username", "users")
    op.drop_index("ix_users_telegram_id", "users")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS order_status")
    op.execute("DROP TYPE IF EXISTS fulfillment_type")
    op.execute("DROP TYPE IF EXISTS product_status")
