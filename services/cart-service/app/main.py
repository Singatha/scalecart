from commerce_common import ServiceSettings, create_service_app, redis_check

settings = ServiceSettings(service_name="cart-service")
checks = {"redis": redis_check(settings.redis_url)} if settings.redis_url else {}
app = create_service_app(
    service_name=settings.service_name,
    cors_origins=settings.cors_origin_list,
    readiness_checks=checks,
    log_level=settings.log_level,
)
