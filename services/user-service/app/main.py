from commerce_common import ServiceSettings, create_service_app, postgres_check

settings = ServiceSettings(service_name="user-service")
checks = {"postgres": postgres_check(settings.database_url)} if settings.database_url else {}
app = create_service_app(
    service_name=settings.service_name,
    cors_origins=settings.cors_origin_list,
    readiness_checks=checks,
    log_level=settings.log_level,
)
