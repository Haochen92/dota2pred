import redis.asyncio as aioredis
import os
from dota_oracle_common.utils.env_loader import load_workspace_env

load_workspace_env()

class RedisClientFactory:
    _instance: aioredis.Redis | None = None
    
    @classmethod
    def create_instance(cls) -> aioredis.Redis:
        if cls._instance is None:
            cls._instance= aioredis.Redis(
                host='localhost',
                port=int(os.getenv("REDIS_PORT", "6379")),
                decode_responses=True
            )
        
        return cls._instance
    
    @classmethod
    async def close_instance(cls) -> None:
        if cls._instance is not None:
            await cls._instance.aclose()
            cls._instance = None