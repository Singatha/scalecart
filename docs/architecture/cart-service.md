# Cart-service contract

The cart service owns temporary shopping intent in Redis. It does not own product names, prices, or
inventory and does not connect to the product database.

## Cart identity

An unauthenticated `GET /api/cart` creates an opaque UUID in the response's `cart_id`. Guest clients
send that value on later requests as `X-Cart-ID`. UUID entropy prevents practical guessing, and the
gateway accepts the header through the shared CORS policy.

When a valid access bearer token is present, its `sub` claim selects the customer cart and `cart_id` is
`null`. Invalid or expired tokens return `401`; they never silently fall back to a guest cart.

`POST /api/cart/merge` requires both an access token and the guest's `X-Cart-ID`. Available guest lines
are combined with customer lines, capped by current stock and the per-item maximum, then the guest key
is deleted. Retrying the merge is safe because the source no longer exists.

## Operations

- `GET /api/cart` reads the cart and reconciles every line with product-service.
- `POST /api/cart/items` accepts `variant_id` and a positive `quantity`.
- `PATCH /api/cart/items/{variant_id}` sets, rather than increments, quantity.
- `DELETE /api/cart/items/{variant_id}` removes a line.
- `DELETE /api/cart` clears all lines.

Adding and updating reject unavailable variants and quantities above current stock. Redis `WATCH`/
`MULTI` transactions retry conflicting writes, preventing lost updates from concurrent browser tabs.
Every read or write refreshes the configured TTL, which defaults to 30 days. A cart defaults to at most
50 distinct lines and 99 units per line to keep request fan-out and Redis values bounded.

## Reconciliation and totals

Stored lines contain names, SKU, price, currency, and image snapshots for continuity. The response uses
the current catalog price and exposes `price_changed`, `available_stock`, and `is_available`. A line is
available only when current stock can satisfy its full quantity. Unavailable lines remain visible for
customer correction but are excluded from `subtotal_amount`.

Amounts remain integer minor units. A cart contains one currency, `item_count` is the sum of quantities,
and `line_total_amount` is the current unit price multiplied by quantity.
