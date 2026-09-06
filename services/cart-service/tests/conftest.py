from collections.abc import AsyncIterator, Callable

import pytest_asyncio
from app.catalog import get_catalog_client
from app.main import app
from app.schemas import CatalogVariant, StoredCart
from app.store import get_cart_store
from httpx import ASGITransport, AsyncClient


class FakeCartStore:
    def __init__(self) -> None:
        self.carts: dict[str, StoredCart] = {}

    async def read(self, key: str) -> StoredCart:
        return self.carts.get(key, StoredCart()).model_copy(deep=True)

    async def mutate(self, key: str, mutation: Callable[[StoredCart], StoredCart]) -> StoredCart:
        cart = mutation(await self.read(key))
        self.carts[key] = cart.model_copy(deep=True)
        return cart

    async def delete(self, key: str) -> None:
        self.carts.pop(key, None)


class FakeCatalogClient:
    def __init__(self) -> None:
        self.variants: dict[str, CatalogVariant] = {}

    async def get_variant(self, variant_id):
        variant = self.variants.get(str(variant_id))
        return variant.model_copy(deep=True) if variant else None


@pytest_asyncio.fixture
async def store() -> FakeCartStore:
    return FakeCartStore()


@pytest_asyncio.fixture
async def catalog() -> FakeCatalogClient:
    return FakeCatalogClient()


@pytest_asyncio.fixture
async def client(store, catalog) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_cart_store] = lambda: store
    app.dependency_overrides[get_catalog_client] = lambda: catalog
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
