from functools import lru_cache

from commerce_common import ServiceSettings


class ProductServiceSettings(ServiceSettings):
    jwt_secret_key: str = "development-only-change-me-use-32-bytes"
    jwt_issuer: str = "scalecart"
    jwt_audience: str = "scalecart-storefront"


@lru_cache
def get_product_settings() -> ProductServiceSettings:
    return ProductServiceSettings(service_name="product-service")
