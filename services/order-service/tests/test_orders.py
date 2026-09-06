from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt

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
        json={"status": "confirmed"},
    )
    assert confirmed.status_code == 200
    cancelled = await client.patch(
        f"/orders/{order['number']}/status",
        headers=admin_headers,
        json={"status": "cancelled"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert inventory.released == [UUID(order["id"])]

    invalid = await client.patch(
        f"/orders/{order['number']}/status",
        headers=admin_headers,
        json={"status": "shipped"},
    )
    assert invalid.status_code == 409
