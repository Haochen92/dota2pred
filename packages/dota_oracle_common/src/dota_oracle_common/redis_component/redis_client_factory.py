import redis.asyncio as aioredis
import os
from dota_oracle_common.utils.env_loader import load_workspace_env
from typing import Optional

load_workspace_env()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380")


class RedisClientFactory:
    _instance: aioredis.Redis | None = None
    _pool: Optional[aioredis.ConnectionPool] = None

    @classmethod
    def create_instance(cls, redis_url: str = REDIS_URL) -> aioredis.Redis:
        if cls._instance is None:

            if cls._pool is None:
                cls._pool = aioredis.ConnectionPool.from_url(
                    redis_url,
                    decode_responses=True,
                    max_connections=20,
                )

            cls._instance = aioredis.Redis(connection_pool=cls._pool)

        return cls._instance

    @classmethod
    async def close_instance(cls) -> None:
        if cls._pool is not None:
            print("Closing explicit Redis connection pool...")
            await cls._pool.disconnect()

            cls._pool = None
            cls._instance = None
