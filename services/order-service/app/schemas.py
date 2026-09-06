from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ShippingAddress(BaseModel):
    recipient_name: str = Field(min_length=1, max_length=200)
    line1: str = Field(min_length=1, max_length=200)
    line2: str | None = Field(default=None, max_length=200)
    city: str = Field(min_length=1, max_length=100)
    region: str = Field(min_length=1, max_length=100)
    postal_code: str = Field(min_length=1, max_length=32)
    country_code: str = Field(min_length=2, max_length=2)
    phone: str | None = Field(default=None, max_length=32)

    @field_validator("country_code")
    @classmethod
    def normalize_country_code(cls, value: str) -> str:
        return value.upper()


class CheckoutCreate(BaseModel):
    email: EmailStr
    delivery_method: Literal["standard", "express"] = "standard"
    shipping_address: ShippingAddress


class CartItemSnapshot(BaseModel):
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


class CartSnapshot(BaseModel):
    cart_id: UUID | None
    items: list[CartItemSnapshot]
    item_count: int
    subtotal_amount: int
    currency: str | None


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: UUID
    variant_id: UUID
    product_slug: str
    product_name: str
    variant_name: str
    sku: str
    quantity: int
    unit_price_amount: int
    line_total_amount: int
    image_url: str | None


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    number: str
    customer_id: UUID | None
    email: EmailStr
    status: str
    currency: str
    subtotal_amount: int
    shipping_amount: int
    total_amount: int
    delivery_method: str
    shipping_address: ShippingAddress
    items: list[OrderItemRead]
    created_at: datetime
    updated_at: datetime


class CheckoutRead(OrderRead):
    access_token: str | None = None


class OrderList(BaseModel):
    items: list[OrderRead]
    total: int
    page: int
    page_size: int
    pages: int


class OrderStatusUpdate(BaseModel):
    status: Literal["confirmed", "processing", "shipped", "delivered", "cancelled"]
