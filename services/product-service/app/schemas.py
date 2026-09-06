from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator, model_validator

CatalogStatus = Literal["draft", "active", "archived"]
Name = Annotated[str, Field(min_length=1, max_length=200)]


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str | None = Field(default=None, min_length=1, max_length=120, pattern=r"^[a-z0-9-]+$")
    description: str | None = None
    parent_id: UUID | None = None
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    slug: str | None = Field(default=None, min_length=1, max_length=120, pattern=r"^[a-z0-9-]+$")
    description: str | None = None
    parent_id: UUID | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    parent_id: UUID | None
    name: str
    slug: str
    description: str | None
    sort_order: int
    is_active: bool


class VariantCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    price_amount: int = Field(ge=0)
    compare_at_amount: int | None = Field(default=None, ge=0)
    currency: str = Field(default="ZAR", min_length=3, max_length=3)
    stock_quantity: int = Field(default=0, ge=0)
    attributes: dict[str, str] = Field(default_factory=dict)

    @field_validator("sku", "currency")
    @classmethod
    def uppercase_value(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def compare_at_is_not_lower(self) -> "VariantCreate":
        if self.compare_at_amount is not None and self.compare_at_amount < self.price_amount:
            raise ValueError("compare_at_amount cannot be lower than price_amount.")
        return self


class VariantUpdate(BaseModel):
    sku: str | None = Field(default=None, min_length=1, max_length=80)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    price_amount: int | None = Field(default=None, ge=0)
    compare_at_amount: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    stock_quantity: int | None = Field(default=None, ge=0)
    attributes: dict[str, str] | None = None
    is_active: bool | None = None

    @field_validator("sku", "currency")
    @classmethod
    def uppercase_value(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else value


class VariantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sku: str
    name: str
    price_amount: int
    compare_at_amount: int | None
    currency: str
    stock_quantity: int
    attributes: dict[str, str]
    is_active: bool


class ImageCreate(BaseModel):
    url: AnyHttpUrl
    alt_text: str = Field(min_length=1, max_length=255)
    position: int = Field(default=0, ge=0)


class ImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    alt_text: str
    position: int


class ProductCreate(BaseModel):
    category_id: UUID
    name: Name
    slug: str | None = Field(default=None, min_length=1, max_length=220, pattern=r"^[a-z0-9-]+$")
    description: str = Field(min_length=1)
    brand: str | None = Field(default=None, max_length=100)
    status: CatalogStatus = "draft"
    featured: bool = False
    variants: list[VariantCreate] = Field(min_length=1)
    images: list[ImageCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def variants_use_one_currency(self) -> "ProductCreate":
        if len({variant.currency for variant in self.variants}) > 1:
            raise ValueError("All variants for a product must use the same currency.")
        return self


class ProductUpdate(BaseModel):
    category_id: UUID | None = None
    name: Name | None = None
    slug: str | None = Field(default=None, min_length=1, max_length=220, pattern=r"^[a-z0-9-]+$")
    description: str | None = Field(default=None, min_length=1)
    brand: str | None = Field(default=None, max_length=100)
    status: CatalogStatus | None = None
    featured: bool | None = None


class ProductSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    brand: str | None
    featured: bool
    category: CategoryRead
    minimum_price_amount: int
    currency: str
    in_stock: bool
    primary_image: str | None


class ProductDetail(ProductSummary):
    description: str
    status: CatalogStatus
    variants: list[VariantRead] = Field(validation_alias="active_variants")
    images: list[ImageRead]
    created_at: datetime
    updated_at: datetime


class ProductList(BaseModel):
    items: list[ProductSummary]
    total: int
    page: int
    page_size: int
    pages: int


class CartVariantRead(BaseModel):
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


class InventoryReservationItem(BaseModel):
    variant_id: UUID
    quantity: int = Field(ge=1)


class InventoryReservationCreate(BaseModel):
    reservation_id: UUID
    items: list[InventoryReservationItem] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def variants_are_unique(self) -> "InventoryReservationCreate":
        if len({item.variant_id for item in self.items}) != len(self.items):
            raise ValueError("Inventory reservation variants must be unique.")
        return self


class InventoryReservationRead(BaseModel):
    reservation_id: UUID
    status: str
