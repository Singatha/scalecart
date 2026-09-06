from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class CatalogVariant(BaseModel):
    product_id: UUID
    product_slug: str
    product_name: str
    variant_id: UUID
    variant_name: str
    sku: str
    price_amount: int
    currency: str
    stock_quantity: int
    image_url: str | None


class StoredCartItem(BaseModel):
    variant_id: UUID
    product_id: UUID
    product_slug: str
    product_name: str
    variant_name: str
    sku: str
    unit_price_amount: int
    currency: str
    quantity: int
    image_url: str | None = None

    @classmethod
    def from_catalog(cls, variant: CatalogVariant, quantity: int) -> "StoredCartItem":
        return cls(
            variant_id=variant.variant_id,
            product_id=variant.product_id,
            product_slug=variant.product_slug,
            product_name=variant.product_name,
            variant_name=variant.variant_name,
            sku=variant.sku,
            unit_price_amount=variant.price_amount,
            currency=variant.currency,
            quantity=quantity,
            image_url=variant.image_url,
        )


class StoredCart(BaseModel):
    items: dict[str, StoredCartItem] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AddCartItem(BaseModel):
    variant_id: UUID
    quantity: int = Field(default=1, ge=1)


class UpdateCartItem(BaseModel):
    quantity: int = Field(ge=1)


class CartItemRead(BaseModel):
    variant_id: UUID
    product_id: UUID
    product_slug: str
    product_name: str
    variant_name: str
    sku: str
    unit_price_amount: int
    currency: str
    quantity: int
    line_total_amount: int
    available_stock: int
    is_available: bool
    price_changed: bool
    image_url: str | None


class CartRead(BaseModel):
    cart_id: UUID | None
    items: list[CartItemRead]
    item_count: int
    subtotal_amount: int
    currency: str | None
    expires_in: int
