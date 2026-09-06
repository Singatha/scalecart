from functools import lru_cache

from commerce_common import ServiceSettings


class CartServiceSettings(ServiceSettings):
    jwt_secret_key: str = "development-only-change-me-use-32-bytes"
    jwt_issuer: str = "scalecart"
    jwt_audience: str = "scalecart-storefront"
    product_service_url: str = "http://product-service:8000"
    cart_ttl_seconds: int = 60 * 60 * 24 * 30
    product_request_timeout_seconds: float = 3.0
    maximum_item_quantity: int = 99
    maximum_cart_items: int = 50


@lru_cache
def get_cart_settings() -> CartServiceSettings:
    return CartServiceSettings(service_name="cart-service")
