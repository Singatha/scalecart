from collections.abc import Callable

from redis.asyncio import Redis
from redis.exceptions import WatchError

from .config import get_cart_settings
from .schemas import StoredCart, utc_now

CartMutation = Callable[[StoredCart], StoredCart]


class RedisCartStore:
    def __init__(self, client: Redis, ttl_seconds: int) -> None:
        self.client = client
        self.ttl_seconds = ttl_seconds

    async def read(self, key: str) -> StoredCart:
        raw = await self.client.get(key)
        if raw is None:
            return StoredCart()
        await self.client.expire(key, self.ttl_seconds)
        return StoredCart.model_validate_json(raw)

    async def mutate(self, key: str, mutation: CartMutation) -> StoredCart:
        async with self.client.pipeline() as pipeline:
            while True:
                try:
                    await pipeline.watch(key)
                    raw = await pipeline.get(key)
                    cart = StoredCart.model_validate_json(raw) if raw else StoredCart()
                    cart = mutation(cart)
                    cart.updated_at = utc_now()
                    pipeline.multi()
                    pipeline.set(key, cart.model_dump_json(), ex=self.ttl_seconds)
                    await pipeline.execute()
                    return cart
                except WatchError:
                    continue
                finally:
                    await pipeline.reset()

    async def delete(self, key: str) -> None:
        await self.client.delete(key)


settings = get_cart_settings()
redis_client = (
    Redis.from_url(settings.redis_url, decode_responses=True) if settings.redis_url else None
)
cart_store = RedisCartStore(redis_client, settings.cart_ttl_seconds) if redis_client else None


async def get_cart_store() -> RedisCartStore:
    if cart_store is None:
        raise RuntimeError("REDIS_URL is required for cart API requests")
    return cart_store
