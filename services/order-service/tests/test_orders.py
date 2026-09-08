from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from app.models import Order
from sqlalchemy import select

CART_ID = "20000000-0000-0000-0000-000000000001"
JWT_SECRET = "development-only-change-me-use-32-bytes"


def token(user_id: UUID, roles: list[str]) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "type": "access",
            "roles": roles,
            "iat": now,
            "exp": now + timedelta(minutes=15),
            "iss": "scalecart",
            "aud": "scalecart-storefront",
        },
        JWT_SECRET,
        algorithm="HS256",
    )


def auth(user_id: UUID, roles: list[str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {token(user_id, roles)}"}


def checkout_headers(**extra: str) -> dict[str, str]:
    return {"X-Cart-ID": CART_ID, "Idempotency-Key": str(uuid4()), **extra}


def checkout_payload(delivery_method: str = "standard") -> dict:
    return {
        "email": "buyer@example.com",
        "delivery_method": delivery_method,
        "shipping_address": {
            "recipient_name": "Ada Buyer",
            "line1": "14 Market Street",
            "city": "Cape Town",
            "region": "Western Cape",
            "postal_code": "8001",
            "country_code": "za",
            "phone": "+27210000000",
        },
    }


async def test_guest_checkout_snapshots_cart_and_supports_private_tracking(
    client, cart, inventory
) -> None:
    response = await client.post("/orders", headers=checkout_headers(), json=checkout_payload())
    assert response.status_code == 201, response.text
    order = response.json()
    assert order["status"] == "pending_payment"
    assert order["subtotal_amount"] == 259800
    assert order["shipping_amount"] == 0
    assert order["total_amount"] == 259800
    assert order["shipping_address"]["country_code"] == "ZA"
    assert order["items"][0]["quantity"] == 2
    assert order["access_token"]
    assert [entry["to_status"] for entry in order["status_history"]] == [
        "reserving_inventory",
        "pending_payment",
    ]
    assert order["reservation_expires_at"] is not None
    assert cart.clear_count == 1
    assert len(inventory.reserved) == 1

    hidden = await client.get(f"/orders/{order['number']}")
    assert hidden.status_code == 404
    tracked = await client.get(
        f"/orders/{order['number']}", headers={"X-Order-Token": order["access_token"]}
    )
    assert tracked.status_code == 200


async def test_checkout_is_idempotent_for_authenticated_customers(client, inventory) -> None:
    user_id = uuid4()
    headers = {
        **auth(user_id, ["customer"]),
        "Idempotency-Key": "checkout-attempt-0001",
    }
    first = await client.post("/orders", headers=headers, json=checkout_payload("express"))
    second = await client.post("/orders", headers=headers, json=checkout_payload("express"))
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["shipping_amount"] == 19900
    assert len(inventory.reserved) == 1

    listing = await client.get("/orders", headers=auth(user_id, ["customer"]))
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["customer_id"] == str(user_id)


async def test_checkout_rejects_empty_or_unavailable_carts(client, cart) -> None:
    cart.cart.items = []
    cart.cart.item_count = 0
    cart.cart.subtotal_amount = 0
    empty = await client.post("/orders", headers=checkout_headers(), json=checkout_payload())
    assert empty.status_code == 409

    cart.cart = cart.__class__().cart
    cart.cart.items[0].is_available = False
    unavailable = await client.post("/orders", headers=checkout_headers(), json=checkout_payload())
    assert unavailable.status_code == 409


async def test_admin_status_transitions_release_cancelled_inventory(client, inventory) -> None:
    created = await client.post("/orders", headers=checkout_headers(), json=checkout_payload())
    order = created.json()
    admin_headers = auth(uuid4(), ["admin"])
    confirmed = await client.patch(
        f"/orders/{order['number']}/status",
        headers=admin_headers,
        json={"status": "confirmed", "reason": "payment_captured"},
    )
    assert confirmed.status_code == 200
    cancelled = await client.patch(
        f"/orders/{order['number']}/status",
        headers=admin_headers,
        json={"status": "cancelled"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["reservation_expires_at"] is None
    assert cancelled.json()["status_history"][-1]["actor_type"] == "admin"
    assert cancelled.json()["status_history"][-1]["reason"] == "administrator_transition"
    assert inventory.released == [UUID(order["id"])]

    invalid = await client.patch(
        f"/orders/{order['number']}/status",
        headers=admin_headers,
        json={"status": "shipped"},
    )
    assert invalid.status_code == 409


async def test_customer_and_guest_cancellation_require_order_ownership(client, inventory) -> None:
    user_id = uuid4()
    customer_headers = {
        **auth(user_id, ["customer"]),
        "Idempotency-Key": "customer-cancellation-0001",
    }
    customer_order = (
        await client.post("/orders", headers=customer_headers, json=checkout_payload())
    ).json()

    hidden = await client.post(
        f"/orders/{customer_order['number']}/cancel",
        headers=auth(uuid4(), ["customer"]),
    )
    assert hidden.status_code == 404

    cancelled = await client.post(
        f"/orders/{customer_order['number']}/cancel",
        headers=auth(user_id, ["customer"]),
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["status_history"][-1]["actor_type"] == "customer"
    assert cancelled.json()["status_history"][-1]["actor_id"] == str(user_id)

    guest_order = (
        await client.post("/orders", headers=checkout_headers(), json=checkout_payload())
    ).json()
    guest_cancelled = await client.post(
        f"/orders/{guest_order['number']}/cancel",
        headers={"X-Order-Token": guest_order["access_token"]},
    )
    assert guest_cancelled.status_code == 200
    assert guest_cancelled.json()["status_history"][-1]["actor_type"] == "guest"
    assert inventory.released == [UUID(customer_order["id"]), UUID(guest_order["id"])]


async def test_expired_reservations_are_released_and_audited(
    client, inventory, session_factory
) -> None:
    created = await client.post("/orders", headers=checkout_headers(), json=checkout_payload())
    order = created.json()
    async with session_factory() as session:
        stored = await session.scalar(select(Order).where(Order.id == UUID(order["id"])))
        assert stored is not None
        stored.reservation_expires_at = datetime.now(UTC) - timedelta(minutes=1)
        await session.commit()

    expired = await client.post(
        "/orders/actions/expire-reservations",
        headers=auth(uuid4(), ["admin"]),
    )
    assert expired.status_code == 200, expired.text
    assert expired.json() == {"expired_count": 1, "order_numbers": [order["number"]]}
    assert inventory.released == [UUID(order["id"])]

    tracked = await client.get(
        f"/orders/{order['number']}", headers={"X-Order-Token": order["access_token"]}
    )
    assert tracked.json()["status"] == "cancelled"
    assert tracked.json()["status_history"][-1]["reason"] == "inventory_reservation_expired"


async def test_expiry_release_can_be_retried_after_dependency_failure(
    client, inventory, session_factory
) -> None:
    created = await client.post("/orders", headers=checkout_headers(), json=checkout_payload())
    order = created.json()
    async with session_factory() as session:
        stored = await session.scalar(select(Order).where(Order.id == UUID(order["id"])))
        assert stored is not None
        stored.reservation_expires_at = datetime.now(UTC) - timedelta(minutes=1)
        await session.commit()

    inventory.release_failures = 1
    admin_headers = auth(uuid4(), ["admin"])
    failed = await client.post("/orders/actions/expire-reservations", headers=admin_headers)
    assert failed.status_code == 503

    retried = await client.post("/orders/actions/expire-reservations", headers=admin_headers)
    assert retried.status_code == 200
    assert retried.json()["expired_count"] == 1
    assert inventory.released == [UUID(order["id"])]


async def test_checkout_recovers_from_transient_reservation_failure(client, inventory) -> None:
    headers = checkout_headers()
    inventory.reserve_failures = 1
    failed = await client.post("/orders", headers=headers, json=checkout_payload())
    assert failed.status_code == 503

    retried = await client.post("/orders", headers=headers, json=checkout_payload())
    assert retried.status_code == 201
    assert retried.json()["status"] == "pending_payment"
    assert [entry["to_status"] for entry in retried.json()["status_history"]] == [
        "reserving_inventory",
        "pending_payment",
    ]
    assert inventory.reserved == [UUID(retried.json()["id"])]


async def test_inventory_rejection_is_terminal_and_audited(
    client, inventory, session_factory
) -> None:
    headers = checkout_headers()
    inventory.unavailable = True
    rejected = await client.post("/orders", headers=headers, json=checkout_payload())
    assert rejected.status_code == 409

    repeated = await client.post("/orders", headers=headers, json=checkout_payload())
    assert repeated.status_code == 409

    async with session_factory() as session:
        order = await session.scalar(
            select(Order).where(Order.idempotency_key == headers["Idempotency-Key"])
        )
        assert order is not None
        assert order.status == "checkout_failed"
        assert order.reservation_expires_at is None
        assert order.status_history[-1].reason == "inventory_unavailable"


async def test_order_listing_can_be_filtered_by_status(client) -> None:
    user_id = uuid4()
    headers = {
        **auth(user_id, ["customer"]),
        "Idempotency-Key": "status-filter-0001",
    }
    await client.post("/orders", headers=headers, json=checkout_payload())

    pending = await client.get(
        "/orders?status=pending_payment", headers=auth(user_id, ["customer"])
    )
    assert pending.status_code == 200
    assert pending.json()["total"] == 1

    cancelled = await client.get("/orders?status=cancelled", headers=auth(user_id, ["customer"]))
    assert cancelled.status_code == 200
    assert cancelled.json()["total"] == 0
