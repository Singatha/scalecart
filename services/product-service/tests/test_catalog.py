from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt

JWT_SECRET = "development-only-change-me-use-32-bytes"


def access_token(roles: list[str]) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(uuid4()),
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


def bearer(roles: list[str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token(roles)}"}


async def create_category(client, name: str = "Home") -> dict:
    response = await client.post(
        "/categories",
        headers=bearer(["admin"]),
        json={"name": name, "description": f"{name} goods"},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_product(
    client,
    category_id: str,
    *,
    name: str = "Linen Throw",
    sku: str = "LINEN-NATURAL",
    price: int = 129900,
    stock: int = 8,
    status: str = "active",
) -> dict:
    response = await client.post(
        "/products",
        headers=bearer(["admin"]),
        json={
            "category_id": category_id,
            "name": name,
            "description": "A substantial woven linen throw for cool evenings.",
            "brand": "Common Ground",
            "status": status,
            "featured": True,
            "variants": [
                {
                    "sku": sku,
                    "name": "Natural",
                    "price_amount": price,
                    "currency": "ZAR",
                    "stock_quantity": stock,
                    "attributes": {"colour": "Natural"},
                }
            ],
            "images": [
                {
                    "url": "https://images.example.com/linen-throw.jpg",
                    "alt_text": "Natural linen throw",
                    "position": 0,
                }
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_catalog_writes_require_an_admin_access_token(client) -> None:
    missing = await client.post("/categories", json={"name": "Home"})
    assert missing.status_code == 401

    customer = await client.post("/categories", headers=bearer(["customer"]), json={"name": "Home"})
    assert customer.status_code == 403


async def test_public_catalog_search_filter_sort_and_pagination(client) -> None:
    home = await create_category(client)
    await create_product(client, home["id"])
    await create_product(
        client,
        home["id"],
        name="Stoneware Cup",
        sku="CUP-SAND",
        price=24900,
        stock=0,
    )
    await create_product(
        client,
        home["id"],
        name="Unreleased Lamp",
        sku="LAMP-DRAFT",
        status="draft",
    )

    listing = await client.get("/products?sort=price_asc&page=1&page_size=1")
    assert listing.status_code == 200
    assert listing.json()["total"] == 2
    assert listing.json()["pages"] == 2
    assert listing.json()["items"][0]["name"] == "Stoneware Cup"

    searched = await client.get("/products?search=linen&in_stock=true")
    assert searched.status_code == 200
    assert [item["slug"] for item in searched.json()["items"]] == ["linen-throw"]

    out_of_stock = await client.get("/products?in_stock=false")
    assert [item["name"] for item in out_of_stock.json()["items"]] == ["Stoneware Cup"]

    category_listing = await client.get(f"/products?category={home['slug']}")
    assert category_listing.json()["total"] == 2


async def test_product_detail_and_variant_inventory_updates(client) -> None:
    category = await create_category(client)
    product = await create_product(client, category["id"])
    assert product["minimum_price_amount"] == 129900
    assert product["in_stock"] is True
    assert product["images"][0]["position"] == 0

    detail = await client.get(f"/products/{product['slug']}")
    assert detail.status_code == 200
    assert detail.json()["variants"][0]["sku"] == "LINEN-NATURAL"

    variant_id = product["variants"][0]["id"]
    inventory = await client.patch(
        f"/products/{product['id']}/variants/{variant_id}",
        headers=bearer(["admin"]),
        json={"stock_quantity": 0},
    )
    assert inventory.status_code == 200
    assert inventory.json()["stock_quantity"] == 0

    refreshed = await client.get(f"/products/{product['slug']}")
    assert refreshed.json()["in_stock"] is False


async def test_archiving_categories_and_products_hides_public_catalog(client) -> None:
    category = await create_category(client)
    product = await create_product(client, category["id"])

    archived_product = await client.delete(f"/products/{product['id']}", headers=bearer(["admin"]))
    assert archived_product.status_code == 204
    assert (await client.get(f"/products/{product['slug']}")).status_code == 404

    second = await create_product(client, category["id"], name="Oak Tray", sku="TRAY-OAK")
    archived_category = await client.delete(
        f"/categories/{category['id']}", headers=bearer(["admin"])
    )
    assert archived_category.status_code == 204
    assert (await client.get(f"/products/{second['slug']}")).status_code == 404
    assert (await client.get("/categories")).json() == []


async def test_catalog_identifiers_are_unique(client) -> None:
    category = await create_category(client)
    duplicate_category = await client.post(
        "/categories", headers=bearer(["admin"]), json={"name": "Home"}
    )
    assert duplicate_category.status_code == 409

    await create_product(client, category["id"])
    duplicate_sku = await client.post(
        "/products",
        headers=bearer(["admin"]),
        json={
            "category_id": category["id"],
            "name": "Different Product",
            "description": "Uses a duplicate stock-keeping unit.",
            "status": "active",
            "variants": [
                {
                    "sku": "LINEN-NATURAL",
                    "name": "Natural",
                    "price_amount": 100,
                }
            ],
        },
    )
    assert duplicate_sku.status_code == 409
