import httpx

from commerce_common import create_service_app, postgres_check, rabbitmq_check

from .config import get_order_settings
from .routes import router

settings = get_order_settings()
checks = {}
if settings.database_url:
    checks["postgres"] = postgres_check(settings.database_url)
if settings.rabbitmq_url:
    checks["rabbitmq"] = rabbitmq_check(settings.rabbitmq_url)


def service_check(base_url: str):
    async def check() -> None:
        async with httpx.AsyncClient(
            base_url=base_url, timeout=settings.service_request_timeout_seconds
        ) as client:
            response = await client.get("/health")
            response.raise_for_status()

    return check


checks["cart"] = service_check(settings.cart_service_url)
checks["product"] = service_check(settings.product_service_url)
app = create_service_app(
    service_name=settings.service_name,
    cors_origins=settings.cors_origin_list,
    readiness_checks=checks,
    log_level=settings.log_level,
)
app.include_router(router)
