# Product-service contract

The product service owns categories, products, variants, stock availability, and ordered product
images. Browser requests use the `/api` gateway prefix; internal service routes omit it.

## Public discovery

`GET /api/categories` returns active categories in configured display order. Categories may reference a
parent category, while the public response remains a flat collection that clients can arrange as
needed.

`GET /api/products` accepts these query parameters:

| Parameter | Meaning |
|---|---|
| `search` | Case-insensitive name, description, or brand match |
| `category` | Exact category slug |
| `min_price`, `max_price` | Variant price bounds in minor currency units |
| `in_stock` | Include products with, or without, available active variants |
| `featured` | Filter the curated featured flag |
| `sort` | `newest`, `price_asc`, `price_desc`, or `name` |
| `page`, `page_size` | One-based pagination; page size is capped at 100 |

The response includes `items`, `total`, `page`, `page_size`, and `pages`. A product summary exposes its
minimum active-variant price, currency, stock availability, and first positioned image.

`GET /api/products/{slug}` adds the full description, active variants, and ordered images. Draft or
archived products and products in inactive categories return `404`.

## Money and inventory

All monetary values are integers in the currency's minor unit. For example, `129900` with currency
`ZAR` represents R1,299.00. Variant stock is a non-negative integer. Phase 5 checkout uses a
private-network reservation contract that locks all requested variants and decrements them in one
transaction. The order ID is the reservation ID, making reserve and release calls idempotent; these
internal routes are not exposed by the gateway.

## Catalog administration

Write endpoints require `Authorization: Bearer <access-token>` and an `admin` role claim:

- `POST /api/categories`, `PATCH /api/categories/{id}`, `DELETE /api/categories/{id}`
- `POST /api/products`, `PATCH /api/products/{id}`, `DELETE /api/products/{id}`
- `POST /api/products/{id}/variants`, `PATCH` or `DELETE` a nested variant
- `POST /api/products/{id}/images`, or `DELETE` a nested image

Category and product deletion is soft archival. Variant deletion deactivates the variant. Image
deletion is physical because images are product-owned metadata. Slugs and SKUs are globally unique;
image positions are unique within a product. Variants for one product must use one currency.

Access tokens are issued by the user service and carry short-lived role claims. The product service
validates their signature, issuer, audience, expiry, and token type without accessing identity tables.

## Sample data

After `make migrate`, run `make seed`. The idempotent catalog seed creates three categories and six
active products if their slugs do not already exist. Development image URLs use `placehold.co`; replace
them through the image administration endpoints for a real deployment.
