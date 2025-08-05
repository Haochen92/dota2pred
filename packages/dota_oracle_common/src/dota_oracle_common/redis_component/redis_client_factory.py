import redis.asyncio as aioredis
import os
from dota_oracle_common.utils.env_loader import load_workspace_env

load_workspace_env()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380")


class RedisClientFactory:
    _instance: aioredis.Redis | None = None

    @classmethod
    def create_instance(cls) -> aioredis.Redis:
        if cls._instance is None:
            cls._instance = aioredis.from_url(REDIS_URL, decode_responses=True)

        return cls._instance

    @classmethod
    async def close_instance(cls) -> None:
        if cls._instance is not None:
            await cls._instance.aclose()
            cls._instance = None
