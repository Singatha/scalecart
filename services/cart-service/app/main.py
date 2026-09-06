import httpx

from commerce_common import create_service_app, redis_check

from .config import get_cart_settings
from .routes import router

settings = get_cart_settings()
checks = {"redis": redis_check(settings.redis_url)} if settings.redis_url else {}


async def product_catalog_check() -> None:
    async with httpx.AsyncClient(
        base_url=settings.product_service_url,
        timeout=settings.product_request_timeout_seconds,
    ) as client:
        response = await client.get("/health")
        response.raise_for_status()


checks["product_catalog"] = product_catalog_check
app = create_service_app(
    service_name=settings.service_name,
    cors_origins=settings.cors_origin_list,
    readiness_checks=checks,
    log_level=settings.log_level,
)
app.include_router(router)
