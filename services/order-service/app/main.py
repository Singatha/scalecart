from commerce_common import ServiceSettings, create_service_app, postgres_check, rabbitmq_check

settings = ServiceSettings(service_name="order-service")
checks = {}
if settings.database_url:
    checks["postgres"] = postgres_check(settings.database_url)
if settings.rabbitmq_url:
    checks["rabbitmq"] = rabbitmq_check(settings.rabbitmq_url)
app = create_service_app(
    service_name=settings.service_name,
    cors_origins=settings.cors_origin_list,
    readiness_checks=checks,
    log_level=settings.log_level,
)
