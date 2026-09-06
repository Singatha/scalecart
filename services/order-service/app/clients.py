from typing import Annotated
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException

from .config import get_order_settings
from .schemas import CartSnapshot


class CartClient:
    async def get_cart(self, headers: dict[str, str]) -> CartSnapshot:
        response = await self._request("GET", "/cart", headers=headers)
        return CartSnapshot.model_validate(response.json())

    async def clear_cart(self, headers: dict[str, str]) -> None:
        await self._request("DELETE", "/cart", headers=headers)

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        settings = get_order_settings()
        try:
            async with httpx.AsyncClient(
                base_url=settings.cart_service_url,
                timeout=settings.service_request_timeout_seconds,
            ) as client:
                response = await client.request(method, path, **kwargs)
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail="The cart service is unavailable.") from exc
        if response.is_error:
            raise HTTPException(status_code=503, detail="The cart could not be validated.")
        return response


class InventoryUnavailableError(Exception):
    pass


class InventoryClient:
    async def reserve(self, order_id: UUID, items: list[dict[str, str | int]]) -> None:
        response = await self._request(
            "POST",
            "/internal/inventory/reservations",
            json={"reservation_id": str(order_id), "items": items},
        )
        if response.status_code == 409:
            raise InventoryUnavailableError
        if response.is_error:
            raise HTTPException(status_code=503, detail="Inventory could not be reserved.")

    async def release(self, order_id: UUID) -> None:
        response = await self._request("DELETE", f"/internal/inventory/reservations/{order_id}")
        if response.is_error and response.status_code != 404:
            raise HTTPException(status_code=503, detail="Inventory could not be released.")

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        settings = get_order_settings()
        try:
            async with httpx.AsyncClient(
                base_url=settings.product_service_url,
                timeout=settings.service_request_timeout_seconds,
            ) as client:
                return await client.request(method, path, **kwargs)
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=503, detail="The product service is unavailable."
            ) from exc


cart_client = CartClient()
inventory_client = InventoryClient()


async def get_cart_client() -> CartClient:
    return cart_client


async def get_inventory_client() -> InventoryClient:
    return inventory_client


CartDependency = Annotated[CartClient, Depends(get_cart_client)]
InventoryDependency = Annotated[InventoryClient, Depends(get_inventory_client)]
