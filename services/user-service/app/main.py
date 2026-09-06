from commerce_common import create_service_app, postgres_check

from .config import get_user_settings
from .routes import auth_router, users_router

settings = get_user_settings()
checks = {"postgres": postgres_check(settings.database_url)} if settings.database_url else {}
app = create_service_app(
    service_name=settings.service_name,
    cors_origins=settings.cors_origin_list,
    readiness_checks=checks,
    log_level=settings.log_level,
)
app.include_router(auth_router)
app.include_router(users_router)
