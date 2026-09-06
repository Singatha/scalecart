from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import get_product_settings

settings = get_product_settings()
engine = (
    create_async_engine(settings.database_url, pool_pre_ping=True)
    if settings.database_url
    else None
)
session_factory = (
    async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession) if engine else None
)


async def get_session() -> AsyncIterator[AsyncSession]:
    if session_factory is None:
        raise RuntimeError("DATABASE_URL is required for catalog API requests")
    async with session_factory() as session:
        yield session
