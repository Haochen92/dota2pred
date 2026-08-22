import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

import redis.asyncio as aioredis

from dota_oracle_common.utils.env_loader import load_workspace_env


load_workspace_env()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380")


class RedisConnection:
    """Own one Redis client and its underlying connection pool."""

    def __init__(self, redis_url: str = REDIS_URL) -> None:
        self.pool = aioredis.ConnectionPool.from_url(
            redis_url,
            decode_responses=True,
            max_connections=100,
            health_check_interval=30,
        )
        self.client = aioredis.Redis(connection_pool=self.pool)

    async def close(self) -> None:
        await self.client.aclose()
        await self.pool.disconnect()


@asynccontextmanager
async def redis_client_resource(redis_url: str = REDIS_URL) -> AsyncIterator[aioredis.Redis]:
    """Yield an application-scoped Redis client and close its pool at shutdown."""
    connection = RedisConnection(redis_url=redis_url)
    try:
        yield connection.client
    finally:
        await connection.close()
