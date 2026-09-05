# System overview

## Phase 1 topology

The browser has one origin and one API authority: NGINX on port 8080. NGINX serves the compiled React application, attaches or forwards a request ID, adds security headers, and routes API paths to services on the private Compose network.

```mermaid
flowchart TB
    Browser --> Gateway[NGINX :8080]
    Gateway --> User[user-service :8000]
    Gateway --> Product[product-service :8000]
    Gateway --> Cart[cart-service :8000]
    Gateway --> Order[order-service :8000]
    Gateway --> Payment[payment-service :8000]
    User --> Users[(commerce_users)]
    Product --> Products[(commerce_products)]
    Order --> Orders[(commerce_orders)]
    Payment --> Payments[(commerce_payments)]
    Cart --> Redis
    Order --> RabbitMQ
    Payment --> RabbitMQ
    Notification[notification-service] --> RabbitMQ
    Prometheus --> User & Product & Cart & Order & Payment & Notification
    Grafana --> Prometheus
```

## Ownership rules

- A service owns its schema and migrations. Another service may use its REST contract or consume an event; it may not connect to that database.
- `python-common` contains only cross-cutting transport and operational concerns. It cannot contain domain models or business rules.
- Redis and RabbitMQ are provisioned now, but domain use begins in later phases.
- All browser API traffic flows through the gateway. Backend container ports remain private.

## Operational contract

Every service provides:

- `/health`: process liveness only
- `/ready`: verifies that required infrastructure is reachable
- `/metrics`: Prometheus exposition format
- `X-Request-ID`: accepts the gateway ID or creates one, includes it in logs and responses
- JSON errors shaped as `{ "error": { "code", "message", "correlation_id", "details?" } }`

## Phase boundary

This foundation contains no commerce tables and no placeholder business behavior. Phase 2 introduces the user-service domain and its first non-empty migration. This keeps migrations and tests coupled to real requirements.
