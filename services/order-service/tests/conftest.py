from collections.abc import AsyncIterator
from uuid import UUID

import pytest_asyncio
from app.clients import get_cart_client, get_inventory_client
from app.database import get_session
from app.main import app
from app.models import Base
from app.schemas import CartItemSnapshot, CartSnapshot
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

VARIANT_ID = UUID("30000000-0000-0000-0000-000000000001")


class FakeCartClient:
    def __init__(self) -> None:
        self.cart = CartSnapshot(
            cart_id=UUID("20000000-0000-0000-0000-000000000001"),
            items=[
                CartItemSnapshot(
                    variant_id=VARIANT_ID,
                    product_id=UUID("40000000-0000-0000-0000-000000000001"),
                    product_slug="woven-linen-throw",
                    product_name="Woven Linen Throw",
                    variant_name="Natural",
                    sku="THROW-LINEN-NATURAL",
                    unit_price_amount=129900,
                    currency="ZAR",
                    quantity=2,
                    line_total_amount=259800,
                    available_stock=8,
                    is_available=True,
                    price_changed=False,
                    image_url="https://images.example.com/throw.jpg",
                )
            ],
            item_count=2,
            subtotal_amount=259800,
            currency="ZAR",
        )
        self.clear_count = 0

    async def get_cart(self, headers: dict[str, str]) -> CartSnapshot:
        return self.cart.model_copy(deep=True)

    async def clear_cart(self, headers: dict[str, str]) -> None:
        self.clear_count += 1


class FakeInventoryClient:
    def __init__(self) -> None:
        self.reserved: list[UUID] = []
        self.released: list[UUID] = []

    async def reserve(self, order_id: UUID, items: list[dict[str, str | int]]) -> None:
        self.reserved.append(order_id)

    async def release(self, order_id: UUID) -> None:
        self.released.append(order_id)


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    database_path = tmp_path / "orders.sqlite3"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def cart() -> FakeCartClient:
    return FakeCartClient()


@pytest_asyncio.fixture
async def inventory() -> FakeInventoryClient:
    return FakeInventoryClient()


@pytest_asyncio.fixture
async def client(session_factory, cart, inventory) -> AsyncIterator[AsyncClient]:
    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_cart_client] = lambda: cart
    app.dependency_overrides[get_inventory_client] = lambda: inventory
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
