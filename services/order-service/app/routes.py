import hashlib
import hmac
import math
import secrets
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .auth import AdminPrincipal, OptionalPrincipal, Principal, RequiredPrincipal
from .clients import CartDependency, InventoryDependency, InventoryUnavailableError
from .config import get_order_settings
from .database import get_session
from .models import Order, OrderItem
from .schemas import CheckoutCreate, CheckoutRead, OrderList, OrderRead, OrderStatusUpdate

router = APIRouter(prefix="/orders", tags=["orders"])
Session = Annotated[AsyncSession, Depends(get_session)]
settings = get_order_settings()

TRANSITIONS = {
    "pending_payment": {"confirmed", "cancelled"},
    "confirmed": {"processing", "cancelled"},
    "processing": {"shipped"},
    "shipped": {"delivered"},
}


def _token_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _guest_token(order_id: UUID) -> str:
    return hmac.new(
        settings.jwt_secret_key.encode(), str(order_id).encode(), hashlib.sha256
    ).hexdigest()


def _order_number() -> str:
    return f"SC-{datetime.now(UTC):%Y%m%d}-{secrets.token_hex(6).upper()}"


def _forwarded_headers(authorization: str | None, cart_id: UUID | None) -> dict[str, str]:
    return {
        **({"Authorization": authorization} if authorization else {}),
        **({"X-Cart-ID": str(cart_id)} if cart_id else {}),
    }


def _identity(principal: Principal | None, cart_id: UUID | None) -> str:
    if principal:
        return f"user:{principal.user_id}"
    if cart_id:
        return f"guest:{cart_id}"
    raise HTTPException(status_code=422, detail="X-Cart-ID is required for guest checkout.")


async def _find_order(session: AsyncSession, number: str) -> Order | None:
    return await session.scalar(
        select(Order).options(selectinload(Order.items)).where(Order.number == number)
    )


def _shipping_amount(subtotal: int, delivery_method: str) -> int:
    if delivery_method == "express":
        return settings.express_shipping_amount
    if subtotal >= settings.free_shipping_threshold_amount:
        return 0
    return settings.standard_shipping_amount


async def _finalize_checkout(
    order: Order,
    session: AsyncSession,
    inventory_client,
    cart_client,
    forwarded_headers: dict[str, str],
) -> None:
    if order.status != "reserving_inventory":
        return
    reservation_items = sorted(
        ({"variant_id": str(item.variant_id), "quantity": item.quantity} for item in order.items),
        key=lambda item: str(item["variant_id"]),
    )
    try:
        await inventory_client.reserve(order.id, reservation_items)
    except InventoryUnavailableError as exc:
        order.status = "checkout_failed"
        await session.commit()
        raise HTTPException(
            status_code=409,
            detail="Inventory changed during checkout. Review the cart and try again.",
        ) from exc
    order.status = "pending_payment"
    await session.commit()
    try:
        await cart_client.clear_cart(forwarded_headers)
    except HTTPException:
        pass


@router.post("", response_model=CheckoutRead, status_code=status.HTTP_201_CREATED)
async def checkout(
    payload: CheckoutCreate,
    session: Session,
    cart_client: CartDependency,
    inventory_client: InventoryDependency,
    principal: OptionalPrincipal,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=128)],
    authorization: Annotated[str | None, Header()] = None,
    cart_id: Annotated[UUID | None, Header(alias="X-Cart-ID")] = None,
) -> CheckoutRead:
    identity = _identity(principal, cart_id)
    forwarded = _forwarded_headers(authorization, cart_id)
    existing = await session.scalar(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.idempotency_key == idempotency_key)
    )
    if existing:
        if existing.checkout_identity != identity:
            raise HTTPException(status_code=409, detail="Idempotency key is already in use.")
        if existing.status == "checkout_failed":
            raise HTTPException(
                status_code=409,
                detail="Inventory changed during checkout. Review the cart and try again.",
            )
        await _finalize_checkout(existing, session, inventory_client, cart_client, forwarded)
        access_token = _guest_token(existing.id) if existing.customer_id is None else None
        return CheckoutRead(
            **OrderRead.model_validate(existing).model_dump(), access_token=access_token
        )

    cart = await cart_client.get_cart(forwarded)
    if not cart.items:
        raise HTTPException(status_code=409, detail="The cart is empty.")
    if cart.currency is None or any(not item.is_available for item in cart.items):
        raise HTTPException(
            status_code=409,
            detail="Every cart item must be available before checkout.",
        )

    shipping = _shipping_amount(cart.subtotal_amount, payload.delivery_method)
    address = payload.shipping_address
    order_id = uuid4()
    guest_token = _guest_token(order_id) if principal is None else None
    order = Order(
        id=order_id,
        number=_order_number(),
        customer_id=principal.user_id if principal else None,
        checkout_identity=identity,
        idempotency_key=idempotency_key,
        guest_token_hash=_token_hash(guest_token) if guest_token else None,
        email=str(payload.email),
        status="reserving_inventory",
        currency=cart.currency,
        subtotal_amount=cart.subtotal_amount,
        shipping_amount=shipping,
        total_amount=cart.subtotal_amount + shipping,
        delivery_method=payload.delivery_method,
        recipient_name=address.recipient_name,
        address_line1=address.line1,
        address_line2=address.line2,
        city=address.city,
        region=address.region,
        postal_code=address.postal_code,
        country_code=address.country_code,
        phone=address.phone,
        items=[
            OrderItem(
                product_id=item.product_id,
                variant_id=item.variant_id,
                product_slug=item.product_slug,
                product_name=item.product_name,
                variant_name=item.variant_name,
                sku=item.sku,
                quantity=item.quantity,
                unit_price_amount=item.unit_price_amount,
                line_total_amount=item.line_total_amount,
                image_url=item.image_url,
            )
            for item in cart.items
        ],
    )
    session.add(order)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        order = await session.scalar(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.idempotency_key == idempotency_key)
        )
        if order is None:
            raise HTTPException(status_code=409, detail="Please retry checkout.") from exc
        if order.checkout_identity != identity:
            raise HTTPException(
                status_code=409, detail="Idempotency key is already in use."
            ) from exc
        guest_token = _guest_token(order.id) if order.customer_id is None else None
    if order.status == "checkout_failed":
        raise HTTPException(
            status_code=409,
            detail="Inventory changed during checkout. Review the cart and try again.",
        )
    await _finalize_checkout(order, session, inventory_client, cart_client, forwarded)
    return CheckoutRead(**OrderRead.model_validate(order).model_dump(), access_token=guest_token)


@router.get("", response_model=OrderList)
async def list_orders(
    principal: RequiredPrincipal,
    session: Session,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> OrderList:
    filters = [Order.customer_id == principal.user_id]
    if "admin" in principal.roles:
        filters = []
    total = await session.scalar(select(func.count()).select_from(Order).where(*filters)) or 0
    result = await session.scalars(
        select(Order)
        .options(selectinload(Order.items))
        .where(*filters)
        .order_by(Order.created_at.desc(), Order.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return OrderList(
        items=[OrderRead.model_validate(order) for order in result],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size),
    )


@router.get("/{number}", response_model=OrderRead)
async def get_order(
    number: str,
    session: Session,
    principal: OptionalPrincipal,
    order_token: Annotated[str | None, Header(alias="X-Order-Token")] = None,
) -> Order:
    order = await _find_order(session, number)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    owner = principal is not None and order.customer_id == principal.user_id
    admin = principal is not None and "admin" in principal.roles
    guest = bool(
        order_token
        and order.guest_token_hash
        and secrets.compare_digest(order.guest_token_hash, _token_hash(order_token))
    )
    if not (owner or admin or guest):
        raise HTTPException(status_code=404, detail="Order not found.")
    return order


@router.patch("/{number}/status", response_model=OrderRead)
async def update_order_status(
    number: str,
    payload: OrderStatusUpdate,
    _: AdminPrincipal,
    session: Session,
    inventory_client: InventoryDependency,
) -> Order:
    order = await _find_order(session, number)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    if payload.status not in TRANSITIONS.get(order.status, set()):
        raise HTTPException(
            status_code=409,
            detail=f"An order cannot move from {order.status} to {payload.status}.",
        )
    if payload.status == "cancelled":
        await inventory_client.release(order.id)
    order.status = payload.status
    await session.commit()
    return order
