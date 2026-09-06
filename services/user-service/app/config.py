from functools import lru_cache

from commerce_common import ServiceSettings


class UserServiceSettings(ServiceSettings):
    jwt_secret_key: str = "development-only-change-me-use-32-bytes"
    jwt_issuer: str = "scalecart"
    jwt_audience: str = "scalecart-storefront"
    access_token_minutes: int = 15
    refresh_token_days: int = 7


@lru_cache
def get_user_settings() -> UserServiceSettings:
    return UserServiceSettings(service_name="user-service")
