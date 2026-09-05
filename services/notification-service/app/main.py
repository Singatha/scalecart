from commerce_common import ServiceSettings, create_service_app, rabbitmq_check

settings = ServiceSettings(service_name="notification-service")
checks = {"rabbitmq": rabbitmq_check(settings.rabbitmq_url)} if settings.rabbitmq_url else {}
app = create_service_app(
    service_name=settings.service_name,
    cors_origins=settings.cors_origin_list,
    readiness_checks=checks,
    log_level=settings.log_level,
)
