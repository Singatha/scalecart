# Delivery roadmap

This document is the working source of truth for ScaleCart's phased delivery. A phase is complete only
when its exit criteria are implemented, documented, and covered by appropriate automated tests.

The first five phases established the platform and a usable checkout path. Phase 5 introduced the
minimum durable order foundation needed by checkout; Phase 6 owns completing and hardening the Order
Service as a domain boundary.

## Delivered phases

| Phase | Milestone | Status | Delivered outcome |
|---|---|---|---|
| 1 | Platform foundation | Complete | Monorepo, service shells, gateway, local infrastructure, observability baseline, and CI |
| 2 | Identity and customer profiles | Complete | Registration, authentication, token rotation, roles, profiles, and addresses |
| 3 | Product catalog | Complete | Categories, products, variants, media, inventory, catalog administration, and discovery |
| 4 | Shopping cart | Complete | Persistent guest and customer carts, live reconciliation, and cart merging |
| 5 | Checkout experience | Complete | Guest/customer checkout, delivery selection, immutable checkout snapshots, and the initial order and inventory-reservation path |

## Upcoming phases

| Phase | Milestone | Exit criteria |
|---|---|---|
| 6 | Order Service | Order ownership and lifecycle are complete, status history is auditable, customer and administrator operations are explicit, cancellation and inventory compensation are reliable, stale reservations are handled, and checkout-to-order integration tests cover failure and retry paths. |
| 7 | Payment Service | Provider-neutral payment intents, idempotent authorization/capture, verified asynchronous webhooks, refunds, payment history, and order/payment state coordination are implemented without storing raw card data. |
| 8 | Domain events and transactional outbox | State changes publish versioned events through a transactional outbox; consumers are idempotent, retries and dead-letter handling are defined, and event contracts are tested. |
| 9 | Notification Service | Order and payment events drive retryable email notifications from templates, with delivery status recorded and local development using a safe mail sink. |
| 10 | Fulfilment and shipping | Shipment creation, carrier-neutral tracking, fulfilment status, delivery estimates, and split or partial fulfilment rules are represented without weakening order history. |
| 11 | Returns and refunds | Eligible items can enter a return workflow; return decisions, inventory disposition, partial/full refunds, and customer-visible statuses are coordinated and auditable. |
| 12 | Customer account experience | The storefront provides sign-in, registration, profile and address management, order history, guest-order association where safe, and return/refund visibility. |
| 13 | Administration experience | Authorized staff can manage catalog, inventory, orders, fulfilment, returns, refunds, and customer roles through a protected operations interface. |
| 14 | Search, merchandising, and caching | Search relevance, facets, sorting, featured collections, cache policy, invalidation, and degraded behavior are production-ready and measured. |
| 15 | Security and privacy hardening | Threat modeling, secret and dependency scanning, rate limits, least privilege, audit coverage, privacy controls, backup/restore checks, and security tests meet the release bar. |
| 16 | Resilience | Timeouts, retry budgets, circuit breaking, bulkheads, graceful degradation, recovery procedures, and dependency-failure tests are in place. |
| 17 | Observability and performance | Service-level indicators, actionable dashboards and alerts, distributed traces, capacity targets, performance budgets, and load-test results are documented. |
| 18 | Architecture decisions and API documentation | Implemented architectural choices have ADRs; public and internal API/event contracts are versioned, discoverable, and supported by usage examples. |
| 19 | Release engineering | CI/CD, environment promotion, migration and rollback procedures, artifact provenance, release checks, and an operational runbook support repeatable releases. |
| 20 | Kubernetes deployment | Production-oriented manifests or charts define workloads, configuration, secrets integration, ingress, autoscaling, disruption budgets, observability, and a verified deployment procedure. |

## Sequencing rules

- Orders remain the source of truth for the commercial transaction; payments and fulfilment react to
  order state rather than duplicating it.
- Payment integration follows the completed Order Service contract.
- Cross-service side effects use the transactional event path once Phase 8 is available.
- Security, resilience, and observability requirements may be added incrementally, but their named
  phases are the release gates for systematic verification.
- A scope change should update this roadmap and any affected architecture document in the same change.

