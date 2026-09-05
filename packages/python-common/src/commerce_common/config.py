from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class ServiceSettings(BaseSettings):
    """Environment-backed settings common to all services."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "scalecart-service"
    environment: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:8080"
    database_url: str | None = None
    redis_url: str | None = None
    rabbitmq_url: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> ServiceSettings:
    return ServiceSettings()
