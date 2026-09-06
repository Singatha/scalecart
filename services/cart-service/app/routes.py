import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials

from .catalog import Catalog, CatalogClient
from .config import get_cart_settings
from .identity import CartIdentity, Identity, bearer, decode_user_id
from .schemas import (
    AddCartItem,
    CartItemRead,
    CartRead,
    CatalogVariant,
    StoredCart,
    StoredCartItem,
    UpdateCartItem,
)
from .store import RedisCartStore, get_cart_store

router = APIRouter(prefix="/cart", tags=["cart"])
Store = Annotated[RedisCartStore, Depends(get_cart_store)]
settings = get_cart_settings()


async def _catalog_variants(
    cart: StoredCart, catalog: CatalogClient
) -> dict[str, CatalogVariant | None]:
    keys = list(cart.items)
    variants = await asyncio.gather(
        *(catalog.get_variant(cart.items[key].variant_id) for key in keys)
    )
    return dict(zip(keys, variants, strict=True))


async def _to_response(
    cart: StoredCart,
    identity: CartIdentity,
    catalog: CatalogClient,
) -> CartRead:
    current = await _catalog_variants(cart, catalog)
    items: list[CartItemRead] = []
    subtotal = 0
    for key, stored in cart.items.items():
        variant = current[key]
        available = variant is not None and variant.stock_quantity >= stored.quantity
        unit_price = variant.price_amount if variant else stored.unit_price_amount
        line_total = unit_price * stored.quantity
        if available:
            subtotal += line_total
        items.append(
            CartItemRead(
                **stored.model_dump(exclude={"unit_price_amount", "image_url"}),
                unit_price_amount=unit_price,
                line_total_amount=line_total,
                available_stock=variant.stock_quantity if variant else 0,
                is_available=available,
                price_changed=variant is not None
                and variant.price_amount != stored.unit_price_amount,
                image_url=variant.image_url if variant else stored.image_url,
            )
        )
    currency = next((item.currency for item in items), None)
    return CartRead(
        cart_id=identity.cart_id,
        items=items,
        item_count=sum(item.quantity for item in items),
        subtotal_amount=subtotal,
        currency=currency,
        expires_in=settings.cart_ttl_seconds,
    )


def _check_quantity(quantity: int, available: int) -> None:
    if quantity > settings.maximum_item_quantity:
        raise HTTPException(
            status_code=422,
            detail=f"A cart item cannot exceed {settings.maximum_item_quantity} units.",
        )
    if quantity > available:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only {available} units are currently available.",
        )


@router.get("", response_model=CartRead)
async def get_cart(identity: Identity, store: Store, catalog: Catalog) -> CartRead:
    return await _to_response(await store.read(identity.key), identity, catalog)


@router.post("/items", response_model=CartRead, status_code=status.HTTP_201_CREATED)
async def add_item(
    payload: AddCartItem,
    identity: Identity,
    store: Store,
    catalog: Catalog,
) -> CartRead:
    variant = await catalog.get_variant(payload.variant_id)
    if variant is None:
        raise HTTPException(status_code=404, detail="Product variant not found.")

    def add(cart: StoredCart) -> StoredCart:
        key = str(payload.variant_id)
        existing = cart.items.get(key)
        if existing is None and len(cart.items) >= settings.maximum_cart_items:
            raise HTTPException(
                status_code=409,
                detail=f"A cart cannot contain more than {settings.maximum_cart_items} items.",
            )
        quantity = payload.quantity + (existing.quantity if existing else 0)
        _check_quantity(quantity, variant.stock_quantity)
        currencies = {
            item.currency for item in cart.items.values() if item.variant_id != payload.variant_id
        }
        if currencies and variant.currency not in currencies:
            raise HTTPException(status_code=409, detail="Cart items must use one currency.")
        cart.items[key] = StoredCartItem.from_catalog(variant, quantity)
        return cart

    cart = await store.mutate(identity.key, add)
    return await _to_response(cart, identity, catalog)


@router.patch("/items/{variant_id}", response_model=CartRead)
async def update_item(
    variant_id: UUID,
    payload: UpdateCartItem,
    identity: Identity,
    store: Store,
    catalog: Catalog,
) -> CartRead:
    variant = await catalog.get_variant(variant_id)
    if variant is None:
        raise HTTPException(status_code=409, detail="This product is no longer available.")
    _check_quantity(payload.quantity, variant.stock_quantity)

    def update(cart: StoredCart) -> StoredCart:
        key = str(variant_id)
        if key not in cart.items:
            raise HTTPException(status_code=404, detail="Cart item not found.")
        cart.items[key] = StoredCartItem.from_catalog(variant, payload.quantity)
        return cart

    cart = await store.mutate(identity.key, update)
    return await _to_response(cart, identity, catalog)


@router.delete("/items/{variant_id}", response_model=CartRead)
async def remove_item(
    variant_id: UUID,
    identity: Identity,
    store: Store,
    catalog: Catalog,
) -> CartRead:
    def remove(cart: StoredCart) -> StoredCart:
        if cart.items.pop(str(variant_id), None) is None:
            raise HTTPException(status_code=404, detail="Cart item not found.")
        return cart

    cart = await store.mutate(identity.key, remove)
    return await _to_response(cart, identity, catalog)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(identity: Identity, store: Store) -> Response:
    await store.delete(identity.key)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/merge", response_model=CartRead)
async def merge_guest_cart(
    store: Store,
    catalog: Catalog,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    guest_cart_id: Annotated[UUID, Header(alias="X-Cart-ID")],
) -> CartRead:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication is required to merge a cart.")
    user_id = decode_user_id(credentials)
    user_identity = CartIdentity(key=f"cart:user:{user_id}", cart_id=None, user_id=user_id)
    guest_key = f"cart:guest:{guest_cart_id}"
    guest = await store.read(guest_key)
    variants = await _catalog_variants(guest, catalog)

    def merge(cart: StoredCart) -> StoredCart:
        mergeable = {
            key
            for key, variant in variants.items()
            if variant is not None and variant.stock_quantity > 0
        }
        if len(set(cart.items) | mergeable) > settings.maximum_cart_items:
            raise HTTPException(
                status_code=409,
                detail=f"The merged cart would exceed {settings.maximum_cart_items} items.",
            )
        currencies = {item.currency for item in cart.items.values()}
        incoming_currencies = {
            variants[key].currency for key in mergeable if variants[key] is not None
        }
        if len(currencies | incoming_currencies) > 1:
            raise HTTPException(
                status_code=409, detail="Carts using different currencies cannot merge."
            )
        for key, guest_item in guest.items.items():
            variant = variants[key]
            if variant is None or variant.stock_quantity == 0:
                continue
            existing = cart.items.get(key)
            quantity = guest_item.quantity + (existing.quantity if existing else 0)
            quantity = min(quantity, variant.stock_quantity, settings.maximum_item_quantity)
            cart.items[key] = StoredCartItem.from_catalog(variant, quantity)
        return cart

    merged = await store.mutate(user_identity.key, merge)
    await store.delete(guest_key)
    return await _to_response(merged, user_identity, catalog)
