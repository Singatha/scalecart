# Order-service contract

Order-service owns checkout orchestration and durable order history in `commerce_orders`. It calls
cart-service and product-service through HTTP contracts and never accesses their stores directly.

## Checkout

`POST /api/orders` requires an `Idempotency-Key` plus the current guest `X-Cart-ID` or access bearer
token. The request supplies contact email, standard or express delivery, and a shipping address. The
service rejects empty carts or any line that cannot be fulfilled at its full quantity.

The order first records immutable product, price, quantity, and address snapshots. Product-service then
atomically locks and decrements all requested variants under the order ID. That inventory reservation
is idempotent, so a retry cannot decrement stock twice. On success the cart is cleared and the order
enters `pending_payment`. Payment authorization is intentionally a Phase 6 concern.

Standard shipping defaults to 99.00 in minor units and becomes free at 1,500.00; express shipping
defaults to 199.00. All thresholds are configurable. Catalog prices are treated as tax-inclusive.

## Access and tracking

Authenticated orders belong to the JWT subject and appear in `GET /api/orders`. Guests receive an
opaque `access_token` when checkout succeeds; the storefront retains it locally and sends it as
`X-Order-Token` when reading `GET /api/orders/{number}`. Unauthorized lookups return `404` to avoid
revealing whether an order number exists.

Administrators may list every order and transition states along this graph:

```text
pending_payment -> confirmed -> processing -> shipped -> delivered
       |              |
       +-> cancelled <-+
```

Cancellation is available only before fulfillment starts and releases the product-service reservation
idempotently. Order rows and item snapshots are retained for audit history.
