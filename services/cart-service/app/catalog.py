from typing import Annotated
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, status

from .config import get_cart_settings
from .schemas import CatalogVariant


class CatalogClient:
    async def get_variant(self, variant_id: UUID) -> CatalogVariant | None:
        settings = get_cart_settings()
        try:
            async with httpx.AsyncClient(
                base_url=settings.product_service_url,
                timeout=settings.product_request_timeout_seconds,
            ) as client:
                response = await client.get(f"/internal/variants/{variant_id}")
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The product catalog is temporarily unavailable.",
            ) from exc
        if response.status_code == 404:
            return None
        if response.is_error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The product catalog is temporarily unavailable.",
            )
        return CatalogVariant.model_validate(response.json())


catalog_client = CatalogClient()


async def get_catalog_client() -> CatalogClient:
    return catalog_client


Catalog = Annotated[CatalogClient, Depends(get_catalog_client)]
