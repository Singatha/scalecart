from collections.abc import Awaitable, Callable

ReadinessCheck = Callable[[], Awaitable[None]]


def postgres_check(database_url: str) -> ReadinessCheck:
    async def check() -> None:
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(database_url, pool_pre_ping=True)
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        finally:
            await engine.dispose()

    return check


def redis_check(redis_url: str) -> ReadinessCheck:
    async def check() -> None:
        from redis.asyncio import Redis

        client = Redis.from_url(redis_url)
        try:
            await client.ping()
        finally:
            await client.aclose()

    return check


def rabbitmq_check(rabbitmq_url: str) -> ReadinessCheck:
    async def check() -> None:
        import aio_pika

        connection = await aio_pika.connect_robust(rabbitmq_url, timeout=3)
        await connection.close()

    return check
