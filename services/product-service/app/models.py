from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    parent: Mapped["Category | None"] = relationship(remote_side="Category.id", lazy="selectin")
    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'active', 'archived')", name="ck_products_status"),
        Index("ix_products_category_status", "category_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(220), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text)
    brand: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    category: Mapped[Category] = relationship(lazy="selectin", back_populates="products")
    variants: Mapped[list["ProductVariant"]] = relationship(
        lazy="selectin", back_populates="product", cascade="all, delete-orphan"
    )
    images: Mapped[list["ProductImage"]] = relationship(
        lazy="selectin",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.position",
    )

    @property
    def minimum_price_amount(self) -> int:
        prices = [variant.price_amount for variant in self.variants if variant.is_active]
        return min(prices) if prices else 0

    @property
    def active_variants(self) -> list["ProductVariant"]:
        return [variant for variant in self.variants if variant.is_active]

    @property
    def currency(self) -> str:
        active = [variant for variant in self.variants if variant.is_active]
        return active[0].currency if active else "ZAR"

    @property
    def in_stock(self) -> bool:
        return any(variant.is_active and variant.stock_quantity > 0 for variant in self.variants)

    @property
    def primary_image(self) -> str | None:
        return self.images[0].url if self.images else None


class ProductVariant(Base):
    __tablename__ = "product_variants"
    __table_args__ = (
        CheckConstraint("price_amount >= 0", name="ck_variants_price_nonnegative"),
        CheckConstraint(
            "compare_at_amount IS NULL OR compare_at_amount >= price_amount",
            name="ck_variants_compare_at_price",
        ),
        CheckConstraint("stock_quantity >= 0", name="ck_variants_stock_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    sku: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    price_amount: Mapped[int] = mapped_column(Integer)
    compare_at_amount: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="ZAR")
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0)
    attributes: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    product: Mapped[Product] = relationship(back_populates="variants")


class ProductImage(Base):
    __tablename__ = "product_images"
    __table_args__ = (
        UniqueConstraint("product_id", "position", name="uq_product_images_position"),
        CheckConstraint("position >= 0", name="ck_product_images_position_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(String(2048))
    alt_text: Mapped[str] = mapped_column(String(255))
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    product: Mapped[Product] = relationship(back_populates="images")


class InventoryReservation(Base):
    __tablename__ = "inventory_reservations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('reserved', 'released')", name="ck_inventory_reservations_status"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    items: Mapped[list[dict[str, str | int]]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="reserved")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
