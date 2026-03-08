from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ProductStatus(str, enum.Enum):
    open = "open"
    waiting_24h = "waiting_24h"
    closed = "closed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    cart_items: Mapped[list["CartItem"]] = relationship(back_populates="user")
    orders: Mapped[list["Order"]] = relationship(back_populates="user")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    article: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    profile: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    thread_width: Mapped[str | None] = mapped_column(String(255), nullable=True)
    color: Mapped[str | None] = mapped_column(String(128), nullable=True)

    min_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    max_weight_per_order: Mapped[int] = mapped_column(Integer, nullable=False, default=25)
    total_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus, name="product_status"), nullable=False, default=ProductStatus.open
    )
    threshold_reached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    """Когда набрали min_weight — с этого момента 24ч до закрытия."""
    collection_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    """Конец окна набора заказов (3 дня). Если к этому времени < min_weight — партия закрывается."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    cart_items: Mapped[list["CartItem"]] = relationship(back_populates="product")
    orders: Mapped[list["Order"]] = relationship(back_populates="product")

    __table_args__ = (
        CheckConstraint("min_weight > 0", name="ck_products_min_weight_positive"),
        CheckConstraint("total_weight >= 0", name="ck_products_total_weight_nonneg"),
        CheckConstraint("max_weight_per_order >= 5", name="ck_products_max_weight_per_order_min"),
        CheckConstraint("max_weight_per_order <= 500", name="ck_products_max_weight_per_order_max"),
        Index("ix_products_status", "status"),
        Index("ix_products_threshold_reached_at", "threshold_reached_at"),
        Index("ix_products_collection_until", "collection_until"),
    )


class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="cart_items")
    product: Mapped["Product"] = relationship(back_populates="cart_items")

    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_cart_user_product"),
        CheckConstraint("weight >= 0", name="ck_cart_weight_nonneg"),
        CheckConstraint("(weight % 5) = 0", name="ck_cart_weight_multiple_of_5"),
        Index("ix_cart_user_id", "user_id"),
        Index("ix_cart_product_id", "product_id"),
    )


class Order(Base):
    __tablename__ = "orders"

    class OrderStatus(str, enum.Enum):
        pending = "pending"
        confirmed = "confirmed"
        cancelled = "cancelled"
        completed = "completed"

    class FulfillmentType(str, enum.Enum):
        pickup = "pickup"
        delivery = "delivery"
        uzum_market = "uzum_market"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    weight_total: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped["OrderStatus"] = mapped_column(
        Enum(OrderStatus, name="order_status"), nullable=False, default=OrderStatus.pending
    )
    fulfillment_type: Mapped["FulfillmentType"] = mapped_column(
        Enum(FulfillmentType, name="fulfillment_type"), nullable=False
    )
    delivery_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="orders")
    product: Mapped["Product"] = relationship(back_populates="orders")

    __table_args__ = (
        CheckConstraint("weight_total > 0", name="ck_orders_weight_positive"),
        Index("ix_orders_created_at", "created_at"),
        Index("ix_orders_status", "status"),
        Index("ix_orders_fulfillment_type", "fulfillment_type"),
    )

