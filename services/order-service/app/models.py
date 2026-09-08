from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('reserving_inventory', 'pending_payment', 'confirmed', 'processing', "
            "'shipped', 'delivered', 'cancelled', 'checkout_failed')",
            name="ck_orders_status",
        ),
        CheckConstraint("subtotal_amount >= 0", name="ck_orders_subtotal_nonnegative"),
        CheckConstraint("shipping_amount >= 0", name="ck_orders_shipping_nonnegative"),
        CheckConstraint("total_amount >= 0", name="ck_orders_total_nonnegative"),
        Index("ix_orders_customer_created", "customer_id", "created_at"),
        Index("ix_orders_reservation_expiry", "status", "reservation_expires_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    customer_id: Mapped[UUID | None] = mapped_column(index=True)
    checkout_identity: Mapped[str] = mapped_column(String(80))
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True)
    guest_token_hash: Mapped[str | None] = mapped_column(String(64))
    email: Mapped[str] = mapped_column(String(320))
    status: Mapped[str] = mapped_column(String(32), default="reserving_inventory", index=True)
    currency: Mapped[str] = mapped_column(String(3))
    subtotal_amount: Mapped[int] = mapped_column(BigInteger)
    shipping_amount: Mapped[int] = mapped_column(BigInteger)
    total_amount: Mapped[int] = mapped_column(BigInteger)
    delivery_method: Mapped[str] = mapped_column(String(20))
    recipient_name: Mapped[str] = mapped_column(String(200))
    address_line1: Mapped[str] = mapped_column(String(200))
    address_line2: Mapped[str | None] = mapped_column(String(200))
    city: Mapped[str] = mapped_column(String(100))
    region: Mapped[str] = mapped_column(String(100))
    postal_code: Mapped[str] = mapped_column(String(32))
    country_code: Mapped[str] = mapped_column(String(2))
    phone: Mapped[str | None] = mapped_column(String(32))
    reservation_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    items: Mapped[list["OrderItem"]] = relationship(
        lazy="selectin", back_populates="order", cascade="all, delete-orphan"
    )
    status_history: Mapped[list["OrderStatusHistory"]] = relationship(
        lazy="selectin",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderStatusHistory.created_at, OrderStatusHistory.id",
    )

    @property
    def shipping_address(self) -> dict[str, str | None]:
        return {
            "recipient_name": self.recipient_name,
            "line1": self.address_line1,
            "line2": self.address_line2,
            "city": self.city,
            "region": self.region,
            "postal_code": self.postal_code,
            "country_code": self.country_code,
            "phone": self.phone,
        }


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        CheckConstraint("unit_price_amount >= 0", name="ck_order_items_price_nonnegative"),
        CheckConstraint("line_total_amount >= 0", name="ck_order_items_total_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[UUID] = mapped_column()
    variant_id: Mapped[UUID] = mapped_column()
    product_slug: Mapped[str] = mapped_column(String(220))
    product_name: Mapped[str] = mapped_column(String(200))
    variant_name: Mapped[str] = mapped_column(String(120))
    sku: Mapped[str] = mapped_column(String(80))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price_amount: Mapped[int] = mapped_column(BigInteger)
    line_total_amount: Mapped[int] = mapped_column(BigInteger)
    image_url: Mapped[str | None] = mapped_column(String(2048))

    order: Mapped[Order] = relationship(back_populates="items")


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"
    __table_args__ = (
        CheckConstraint(
            "from_status IS NULL OR from_status IN ('reserving_inventory', 'pending_payment', "
            "'confirmed', 'processing', 'shipped', 'delivered', 'cancelled', "
            "'checkout_failed')",
            name="ck_order_status_history_from_status",
        ),
        CheckConstraint(
            "to_status IN ('reserving_inventory', 'pending_payment', 'confirmed', 'processing', "
            "'shipped', 'delivered', 'cancelled', 'checkout_failed')",
            name="ck_order_status_history_to_status",
        ),
        CheckConstraint(
            "actor_type IN ('system', 'customer', 'guest', 'admin', 'migration')",
            name="ck_order_status_history_actor_type",
        ),
        Index("ix_order_status_history_order_created", "order_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    from_status: Mapped[str | None] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32))
    actor_type: Mapped[str] = mapped_column(String(20))
    actor_id: Mapped[UUID | None] = mapped_column()
    reason: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    order: Mapped[Order] = relationship(back_populates="status_history")
