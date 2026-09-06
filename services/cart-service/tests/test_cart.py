from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from app.schemas import CatalogVariant

CART_ID = UUID("20000000-0000-0000-0000-000000000001")
VARIANT_ID = UUID("30000000-0000-0000-0000-000000000001")


def guest_headers(cart_id: UUID = CART_ID) -> dict[str, str]:
    return {"X-Cart-ID": str(cart_id)}


def user_headers(user_id: UUID) -> dict[str, str]:
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(user_id),
            "type": "access",
            "roles": ["customer"],
            "iat": now,
            "exp": now + timedelta(minutes=15),
            "iss": "scalecart",
            "aud": "scalecart-storefront",
        },
        "development-only-change-me-use-32-bytes",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def stock_variant(stock: int = 8, price: int = 129900) -> CatalogVariant:
    return CatalogVariant(
        product_id=UUID("40000000-0000-0000-0000-000000000001"),
        product_slug="woven-linen-throw",
        product_name="Woven Linen Throw",
        variant_id=VARIANT_ID,
        variant_name="Natural",
        sku="THROW-LINEN-NATURAL",
        price_amount=price,
        currency="ZAR",
        stock_quantity=stock,
        image_url="https://images.example.com/throw.jpg",
    )


async def test_guest_cart_is_created_and_isolated(client, catalog) -> None:
    catalog.variants[str(VARIANT_ID)] = stock_variant()
    empty = await client.get("/cart")
    assert empty.status_code == 200
    assert empty.json()["cart_id"]
    assert empty.json()["items"] == []

    added = await client.post(
        "/cart/items",
        headers=guest_headers(),
        json={"variant_id": str(VARIANT_ID), "quantity": 2},
    )
    assert added.status_code == 201
    assert added.json()["item_count"] == 2
    assert added.json()["subtotal_amount"] == 259800

    other = await client.get("/cart", headers=guest_headers(uuid4()))
    assert other.json()["items"] == []


async def test_add_update_remove_and_stock_limits(client, catalog) -> None:
    catalog.variants[str(VARIANT_ID)] = stock_variant(stock=3)
    await client.post(
        "/cart/items",
        headers=guest_headers(),
        json={"variant_id": str(VARIANT_ID), "quantity": 2},
    )
    too_many = await client.post(
        "/cart/items",
        headers=guest_headers(),
        json={"variant_id": str(VARIANT_ID), "quantity": 2},
    )
    assert too_many.status_code == 409

    updated = await client.patch(
        f"/cart/items/{VARIANT_ID}", headers=guest_headers(), json={"quantity": 1}
    )
    assert updated.status_code == 200
    assert updated.json()["items"][0]["quantity"] == 1

    removed = await client.delete(f"/cart/items/{VARIANT_ID}", headers=guest_headers())
    assert removed.status_code == 200
    assert removed.json()["item_count"] == 0


async def test_cart_reconciles_price_and_availability(client, catalog) -> None:
    catalog.variants[str(VARIANT_ID)] = stock_variant()
    await client.post(
        "/cart/items",
        headers=guest_headers(),
        json={"variant_id": str(VARIANT_ID), "quantity": 2},
    )

    catalog.variants[str(VARIANT_ID)] = stock_variant(stock=1, price=139900)
    reconciled = await client.get("/cart", headers=guest_headers())
    item = reconciled.json()["items"][0]
    assert item["price_changed"] is True
    assert item["unit_price_amount"] == 139900
    assert item["is_available"] is False
    assert reconciled.json()["subtotal_amount"] == 0


async def test_guest_cart_merges_into_authenticated_cart(client, catalog, store) -> None:
    catalog.variants[str(VARIANT_ID)] = stock_variant(stock=5)
    await client.post(
        "/cart/items",
        headers=guest_headers(),
        json={"variant_id": str(VARIANT_ID), "quantity": 2},
    )
    user_id = uuid4()
    merged = await client.post(
        "/cart/merge",
        headers={**user_headers(user_id), **guest_headers()},
    )
    assert merged.status_code == 200
    assert merged.json()["cart_id"] is None
    assert merged.json()["item_count"] == 2
    assert f"cart:guest:{CART_ID}" not in store.carts

    authenticated = await client.get("/cart", headers=user_headers(user_id))
    assert authenticated.json()["item_count"] == 2


async def test_invalid_tokens_are_not_treated_as_guest_carts(client) -> None:
    response = await client.get("/cart", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401
