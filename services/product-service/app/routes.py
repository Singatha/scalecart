import math
import re
import unicodedata
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import Select, exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .auth import AdminPrincipal
from .database import get_session
from .models import Category, Product, ProductImage, ProductVariant
from .schemas import (
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
    ImageCreate,
    ImageRead,
    ProductCreate,
    ProductDetail,
    ProductList,
    ProductUpdate,
    VariantCreate,
    VariantRead,
    VariantUpdate,
)

router = APIRouter()
Session = Annotated[AsyncSession, Depends(get_session)]


def slugify(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
    if not slug:
        raise HTTPException(status_code=422, detail="A URL slug could not be generated.")
    return slug


def _catalog_options() -> tuple:
    return (
        selectinload(Product.category),
        selectinload(Product.variants),
        selectinload(Product.images),
    )


async def _commit_or_conflict(session, message: str) -> None:
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc


async def _category_or_404(session, category_id: UUID) -> Category:
    category = await session.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")
    return category


async def _validate_parent(session, parent_id: UUID, category_id: UUID | None = None) -> Category:
    parent = await _category_or_404(session, parent_id)
    current: Category | None = parent
    visited: set[UUID] = set()
    while current is not None and current.id not in visited:
        if current.id == category_id:
            raise HTTPException(
                status_code=422, detail="Category hierarchy cannot contain a cycle."
            )
        visited.add(current.id)
        current = (
            await session.get(Category, current.parent_id)
            if current.parent_id is not None
            else None
        )
    return parent


async def _product_or_404(session, product_id: UUID) -> Product:
    product = await session.scalar(
        select(Product).options(*_catalog_options()).where(Product.id == product_id)
    )
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    return product


@router.get("/categories", response_model=list[CategoryRead], tags=["catalog"])
async def list_categories(session: Session) -> list[Category]:
    result = await session.scalars(
        select(Category)
        .where(Category.is_active.is_(True))
        .order_by(Category.sort_order, Category.name)
    )
    return list(result)


@router.get("/categories/{slug}", response_model=CategoryRead, tags=["catalog"])
async def get_category(slug: str, session: Session) -> Category:
    category = await session.scalar(
        select(Category).where(Category.slug == slug, Category.is_active.is_(True))
    )
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")
    return category


@router.get("/products", response_model=ProductList, tags=["catalog"])
async def list_products(
    session: Session,
    search: str | None = Query(default=None, min_length=1, max_length=100),
    category: str | None = None,
    min_price: int | None = Query(default=None, ge=0),
    max_price: int | None = Query(default=None, ge=0),
    in_stock: bool | None = None,
    featured: bool | None = None,
    sort: Literal["newest", "price_asc", "price_desc", "name"] = "newest",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=100),
) -> ProductList:
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=422, detail="min_price cannot exceed max_price.")
    filters = [Product.status == "active", Category.is_active.is_(True)]
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                Product.name.ilike(pattern),
                Product.description.ilike(pattern),
                Product.brand.ilike(pattern),
            )
        )
    if category:
        filters.append(Category.slug == category)
    if featured is not None:
        filters.append(Product.featured.is_(featured))
    variant_filters = [
        ProductVariant.product_id == Product.id,
        ProductVariant.is_active.is_(True),
    ]
    if min_price is not None:
        variant_filters.append(ProductVariant.price_amount >= min_price)
    if max_price is not None:
        variant_filters.append(ProductVariant.price_amount <= max_price)
    if in_stock is True:
        variant_filters.append(ProductVariant.stock_quantity > 0)
    if min_price is not None or max_price is not None or in_stock is True:
        filters.append(exists(select(ProductVariant.id).where(*variant_filters)))
    if in_stock is False:
        filters.append(
            ~exists(
                select(ProductVariant.id).where(
                    ProductVariant.product_id == Product.id,
                    ProductVariant.is_active.is_(True),
                    ProductVariant.stock_quantity > 0,
                )
            )
        )

    total = await session.scalar(
        select(func.count()).select_from(Product).join(Category).where(*filters)
    )
    minimum_price = (
        select(func.min(ProductVariant.price_amount))
        .where(
            ProductVariant.product_id == Product.id,
            ProductVariant.is_active.is_(True),
        )
        .correlate(Product)
        .scalar_subquery()
    )
    order_by = {
        "newest": Product.created_at.desc(),
        "price_asc": minimum_price.asc(),
        "price_desc": minimum_price.desc(),
        "name": Product.name.asc(),
    }[sort]
    statement: Select = (
        select(Product)
        .join(Category)
        .options(*_catalog_options())
        .where(*filters)
        .order_by(order_by, Product.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    products = list(await session.scalars(statement))
    count = total or 0
    return ProductList(
        items=products,
        total=count,
        page=page,
        page_size=page_size,
        pages=math.ceil(count / page_size),
    )


@router.get("/products/{slug}", response_model=ProductDetail, tags=["catalog"])
async def get_product(slug: str, session: Session) -> Product:
    product = await session.scalar(
        select(Product)
        .join(Category)
        .options(*_catalog_options())
        .where(
            Product.slug == slug,
            Product.status == "active",
            Category.is_active.is_(True),
        )
    )
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    return product


@router.post(
    "/categories",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
    tags=["catalog-admin"],
)
async def create_category(
    payload: CategoryCreate,
    _: AdminPrincipal,
    session: Session,
) -> Category:
    if payload.parent_id:
        await _validate_parent(session, payload.parent_id)
    category = Category(
        **payload.model_dump(exclude={"slug"}),
        slug=payload.slug or slugify(payload.name),
    )
    session.add(category)
    await _commit_or_conflict(session, "Category slug already exists.")
    await session.refresh(category)
    return category


@router.patch("/categories/{category_id}", response_model=CategoryRead, tags=["catalog-admin"])
async def update_category(
    category_id: UUID,
    payload: CategoryUpdate,
    _: AdminPrincipal,
    session: Session,
) -> Category:
    category = await _category_or_404(session, category_id)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("parent_id"):
        await _validate_parent(session, changes["parent_id"], category.id)
    for name, value in changes.items():
        setattr(category, name, value.strip() if isinstance(value, str) else value)
    await _commit_or_conflict(session, "Category slug already exists.")
    await session.refresh(category)
    return category


@router.delete("/categories/{category_id}", status_code=204, tags=["catalog-admin"])
async def archive_category(
    category_id: UUID,
    _: AdminPrincipal,
    session: Session,
) -> Response:
    category = await _category_or_404(session, category_id)
    category.is_active = False
    await session.commit()
    return Response(status_code=204)


@router.post(
    "/products",
    response_model=ProductDetail,
    status_code=status.HTTP_201_CREATED,
    tags=["catalog-admin"],
)
async def create_product(
    payload: ProductCreate,
    _: AdminPrincipal,
    session: Session,
) -> Product:
    category = await _category_or_404(session, payload.category_id)
    product = Product(
        category=category,
        name=payload.name.strip(),
        slug=payload.slug or slugify(payload.name),
        description=payload.description.strip(),
        brand=payload.brand.strip() if payload.brand else None,
        status=payload.status,
        featured=payload.featured,
        variants=[ProductVariant(**variant.model_dump()) for variant in payload.variants],
        images=[ProductImage(**image.model_dump(mode="json")) for image in payload.images],
    )
    session.add(product)
    await _commit_or_conflict(session, "Product slug, SKU, or image position already exists.")
    return product


@router.patch("/products/{product_id}", response_model=ProductDetail, tags=["catalog-admin"])
async def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    _: AdminPrincipal,
    session: Session,
) -> Product:
    product = await _product_or_404(session, product_id)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("category_id"):
        product.category = await _category_or_404(session, changes.pop("category_id"))
    for name, value in changes.items():
        setattr(product, name, value.strip() if isinstance(value, str) else value)
    await _commit_or_conflict(session, "Product slug already exists.")
    return product


@router.delete("/products/{product_id}", status_code=204, tags=["catalog-admin"])
async def archive_product(
    product_id: UUID,
    _: AdminPrincipal,
    session: Session,
) -> Response:
    product = await _product_or_404(session, product_id)
    product.status = "archived"
    await session.commit()
    return Response(status_code=204)


@router.post(
    "/products/{product_id}/variants",
    response_model=VariantRead,
    status_code=201,
    tags=["catalog-admin"],
)
async def create_variant(
    product_id: UUID,
    payload: VariantCreate,
    _: AdminPrincipal,
    session: Session,
) -> ProductVariant:
    product = await _product_or_404(session, product_id)
    if product.variants and payload.currency != product.currency:
        raise HTTPException(status_code=422, detail="Variant currency must match the product.")
    variant = ProductVariant(product_id=product.id, **payload.model_dump())
    session.add(variant)
    await _commit_or_conflict(session, "Variant SKU already exists.")
    await session.refresh(variant)
    return variant


@router.patch(
    "/products/{product_id}/variants/{variant_id}",
    response_model=VariantRead,
    tags=["catalog-admin"],
)
async def update_variant(
    product_id: UUID,
    variant_id: UUID,
    payload: VariantUpdate,
    _: AdminPrincipal,
    session: Session,
) -> ProductVariant:
    product = await _product_or_404(session, product_id)
    variant = next((item for item in product.variants if item.id == variant_id), None)
    if variant is None:
        raise HTTPException(status_code=404, detail="Variant not found.")
    changes = payload.model_dump(exclude_unset=True)
    new_price = changes.get("price_amount", variant.price_amount)
    new_compare = changes.get("compare_at_amount", variant.compare_at_amount)
    if new_compare is not None and new_compare < new_price:
        raise HTTPException(status_code=422, detail="compare_at_amount cannot be lower than price.")
    new_currency = changes.get("currency", variant.currency)
    if new_currency != product.currency:
        raise HTTPException(status_code=422, detail="Variant currency must match the product.")
    for name, value in changes.items():
        setattr(variant, name, value)
    await _commit_or_conflict(session, "Variant SKU already exists.")
    await session.refresh(variant)
    return variant


@router.delete(
    "/products/{product_id}/variants/{variant_id}", status_code=204, tags=["catalog-admin"]
)
async def archive_variant(
    product_id: UUID,
    variant_id: UUID,
    _: AdminPrincipal,
    session: Session,
) -> Response:
    product = await _product_or_404(session, product_id)
    variant = next((item for item in product.variants if item.id == variant_id), None)
    if variant is None:
        raise HTTPException(status_code=404, detail="Variant not found.")
    variant.is_active = False
    await session.commit()
    return Response(status_code=204)


@router.post(
    "/products/{product_id}/images",
    response_model=ImageRead,
    status_code=201,
    tags=["catalog-admin"],
)
async def create_image(
    product_id: UUID,
    payload: ImageCreate,
    _: AdminPrincipal,
    session: Session,
) -> ProductImage:
    product = await _product_or_404(session, product_id)
    image = ProductImage(product_id=product.id, **payload.model_dump(mode="json"))
    session.add(image)
    await _commit_or_conflict(session, "Image position already exists for this product.")
    await session.refresh(image)
    return image


@router.delete("/products/{product_id}/images/{image_id}", status_code=204, tags=["catalog-admin"])
async def delete_image(
    product_id: UUID,
    image_id: UUID,
    _: AdminPrincipal,
    session: Session,
) -> Response:
    image = await session.scalar(
        select(ProductImage).where(
            ProductImage.id == image_id, ProductImage.product_id == product_id
        )
    )
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found.")
    await session.delete(image)
    await session.commit()
    return Response(status_code=204)
