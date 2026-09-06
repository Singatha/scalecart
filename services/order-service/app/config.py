from functools import lru_cache

from commerce_common import ServiceSettings


class OrderServiceSettings(ServiceSettings):
    jwt_secret_key: str = "development-only-change-me-use-32-bytes"
    jwt_issuer: str = "scalecart"
    jwt_audience: str = "scalecart-storefront"
    cart_service_url: str = "http://cart-service:8000"
    product_service_url: str = "http://product-service:8000"
    service_request_timeout_seconds: float = 5.0
    standard_shipping_amount: int = 9900
    express_shipping_amount: int = 19900
    free_shipping_threshold_amount: int = 150000


@lru_cache
def get_order_settings() -> OrderServiceSettings:
    return OrderServiceSettings(service_name="order-service")
