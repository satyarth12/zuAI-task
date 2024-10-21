from dataclasses import dataclass, field
from typing import Any, Optional

from redis.asyncio import Redis

from server import LOGGER, server_settings


@dataclass
class RedisCacheRepository:
    """
    A repository class for interacting with Redis cache.

    This class provides methods to connect to a Redis server, set and get values,
    delete keys, and check for key existence. It uses asyncio for non-blocking
    operations.

    Attributes:
        host (str): The Redis server host.
        port (int): The Redis server port.
        password (str): The Redis server password.
        _redis (Optional[Redis]): The Redis client instance.

    Methods:
        connect(): Establishes a connection to the Redis server.
        disconnect(): Closes the connection to the Redis server.
        set(key, value, expiration): Sets a key-value pair in the cache.
        get(key): Retrieves a value from the cache by key.
        delete(key): Deletes a key-value pair from the cache.
        exists(key): Checks if a key exists in the cache.
    """

    host: str = field(default_factory=lambda: server_settings.REDIS_HOST)
    port: int = field(default_factory=lambda: server_settings.REDIS_PORT)
    password: str = field(default_factory=lambda: server_settings.REDIS_PASSWORD)
    _redis: Optional[Redis] = None

    async def connect(self) -> None:
        if self._redis is None:
            try:
                self._redis = await Redis.from_url(
                    f"redis://{self.host}:{self.port}",
                    password=self.password,
                    encoding="utf-8",
                    decode_responses=True,
                    max_connections=server_settings.REDIS_MAX_CONNECTIONS,
                )
                LOGGER.info("Connected to Redis")
            except Exception as e:
                LOGGER.error(f"Failed to connect to Redis: {str(e)}")
                raise

    async def disconnect(self) -> None:
        if self._redis is not None:
            await self._redis.close()
            self._redis = None
            LOGGER.info("Disconnected from Redis")

    async def set(self, key: str, value: Any, expiration: int = None) -> None:
        await self._ensure_connection()
        await self._redis.set(key, value, ex=expiration)

    async def get(self, key: str) -> Any:
        await self._ensure_connection()
        return await self._redis.get(key)

    async def delete(self, key: str) -> None:
        await self._ensure_connection()
        await self._redis.delete(key)

    async def exists(self, key: str) -> bool:
        await self._ensure_connection()
        return await self._redis.exists(key) > 0

    async def _ensure_connection(self) -> None:
        if self._redis is None:
            await self.connect()


async def get_redis_cache():
    cache = RedisCacheRepository()
    await cache.connect()
    return cache
